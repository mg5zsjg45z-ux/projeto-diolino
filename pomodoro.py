"""Offline focus timer. Only explicit confirmation creates study records."""
import json
import math
import time
import uuid
from datetime import datetime


class Pomodoro:
    KEY = 'pomodoro_v1'

    def __init__(self, store, clock=time.monotonic):
        self.store, self.clock = store, clock
        self.state = dict(focus=25, short=5, long=15, phase='focus', elapsed=0.0,
                          running=False, pending=False, cycles=0, session=None)
        row = store.conn.execute('SELECT value FROM preferences WHERE key=?', (self.KEY,)).fetchone()
        if row:
            self.state.update(json.loads(row[0]))
        # Closed-app time never becomes study time. Resume is always deliberate.
        self.state['running'] = False
        self.last = clock()
        self.persist()

    def persist(self):
        with self.store.conn:
            self.store.conn.execute('INSERT OR REPLACE INTO preferences(key,value) VALUES(?,?)',
                                    (self.KEY, json.dumps(self.state, ensure_ascii=False)))

    @property
    def duration(self):
        key = {'focus': 'focus', 'short': 'short', 'long': 'long'}[self.state['phase']]
        return self.state[key] * 60

    @property
    def remaining(self):
        return max(0, math.ceil(self.duration - self.state['elapsed']))

    def configure(self, focus, short, long):
        if self.state['elapsed'] or self.state['running'] or self.state['pending']:
            raise ValueError('Termine a sessão atual antes de alterar as durações.')
        values = (int(focus), int(short), int(long))
        if any(not 1 <= value <= 180 for value in values):
            raise ValueError('Use durações inteiras entre 1 e 180 minutos.')
        self.state.update(zip(('focus', 'short', 'long'), values))
        self.persist()

    def start(self, kind='study', topic='', now=None, study_format='Leitura'):
        if self.state['pending'] or self.state['running']:
            return
        if self.state['phase'] == 'focus' and self.state['session'] is None:
            if kind not in ('study', 'bible') or not topic.strip():
                raise ValueError('Informe o tema ou a passagem antes de iniciar.')
            if study_format not in ('Leitura', 'Vídeo', 'Leitura e vídeo'):
                raise ValueError('Selecione o formato do estudo.')
            now = now or datetime.now()
            self.state['session'] = dict(id=uuid.uuid4().hex, kind=kind, topic=topic.strip(),
                                         date=now.date().isoformat(), time=now.strftime('%H:%M'), format=study_format)
        self.last = self.clock()
        self.state['running'] = True
        self.persist()

    def tick(self):
        now = self.clock()
        gap, self.last = max(0, now - self.last), now
        if not self.state['running']:
            return None
        # Suspend/blocked UI: don't count an unattended interval as focused work.
        if gap > 10:
            self.state['running'] = False
            self.persist()
            return 'interrupted'
        self.state['elapsed'] = min(self.duration, self.state['elapsed'] + gap)
        if self.remaining == 0:
            self.state['running'] = False
            if self.state['phase'] == 'focus':
                self.state['pending'] = True
            else:
                self.state.update(phase='focus', elapsed=0.0)
            self.persist()
            return 'finished'
        return None

    def pause(self):
        self.tick()
        self.state['running'] = False
        self.persist()

    def finish_early(self):
        if self.state['phase'] != 'focus':
            return
        self.pause()
        if self.state['elapsed'] < 6:
            raise ValueError('São necessários pelo menos 6 segundos para registrar 0,1 minuto.')
        self.state['pending'] = True
        self.persist()

    def resolve(self, save):
        if not self.state['pending']:
            return None
        session = self.state['session']
        rid = None
        if save:
            values = dict(date=session['date'], time=session['time'],
                          notes='Sessão Pomodoro. Descansos excluídos do tempo de foco.')
            minutes = math.floor(self.state['elapsed'] / 6) / 10
            if session['kind'] == 'study':
                values.update(topic=session['topic'], duration_min=minutes, format=session['format'],
                              source='Pomodoro', learning='')
            else:
                values.update(passage=session['topic'],
                              reflection=f'Foco registrado: {minutes:g} min (sem contar as pausas).')
            # Record and receipt commit together, preventing duplicate confirmation after a crash.
            rid = self.store.save(session['kind'], values,
                                  idempotency_key=f"pomodoro_record:{session['id']}")
        completed = self.state['elapsed'] >= self.duration
        if completed:
            self.state['cycles'] += 1
        self.state.update(phase=('long' if self.state['cycles'] % 4 == 0 else 'short')
                          if completed else 'focus', elapsed=0.0, pending=False, session=None)
        self.persist()
        return rid

    def skip_break(self):
        if self.state['phase'] != 'focus':
            self.state.update(phase='focus', elapsed=0.0, running=False)
            self.persist()
