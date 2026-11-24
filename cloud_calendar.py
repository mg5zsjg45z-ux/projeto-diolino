"""Private, opt-in iCloud calendar synchronization. No invitations are sent."""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid
from urllib.parse import urlparse, quote
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Alarm

ZONE = ZoneInfo('America/Fortaleza')
AGENDA_KEYS = ('date', 'time', 'duration_min', 'title', 'category', 'state', 'reminder', 'description')
APPLE_HELP = 'https://support.apple.com/pt-br/102654'
SERIES_PREFIX = 'diolino-occurrence:'


class CalendarError(Exception):
    pass


class ConcurrentChange(CalendarError):
    pass


def connection_error_message(exc):
    """Do not expose exception bodies, URLs, response data or credentials."""
    if isinstance(exc, CalendarError):
        return str(exc)
    name = type(exc).__name__
    if name == 'AuthorizationError':
        return 'A Apple recusou o acesso. Confira a Conta Apple, a senha específica de app e a permissão do calendário.'
    if name in ('Timeout', 'ReadTimeout', 'ConnectTimeout', 'ConnectionError', 'SSLError'):
        return 'Não foi possível alcançar o iCloud. Confira a conexão com a internet e tente novamente.'
    return 'A integração encontrou uma falha interna ao acessar o calendário. Seus registros foram preservados. Tente novamente após atualizar o aplicativo.'


def fingerprint(value):
    if isinstance(value, dict):
        deleted = value.get('deleted_at')
        value = {key: value.get(key) or (None if key == 'duration_min' else '') for key in AGENDA_KEYS}
        if deleted:
            value['state'] = 'Cancelado'
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, str):
        value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def icloud_url(value):
    parsed = urlparse(str(value))
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443) or not parsed.hostname or not (parsed.hostname == 'icloud.com' or parsed.hostname.endswith('.icloud.com')):
        raise CalendarError('Endereço de calendário inválido. Use apenas um calendário descoberto na sua conta iCloud.')
    return str(value)


class PrivateSettings:
    """DPAPI, scoped to the current Windows user; never part of DB exports."""
    def __init__(self, directory):
        self.path = Path(directory) / 'icloud-connection.bin'

    @staticmethod
    def crypt(data, decrypt=False):
        if os.name != 'nt':
            raise CalendarError('A conexão protegida com o iCloud requer Windows.')
        class Blob(C.Structure):
            _fields_ = [('size', W.DWORD), ('data', C.POINTER(C.c_ubyte))]
        buf = C.create_string_buffer(data)
        incoming = Blob(len(data), C.cast(buf, C.POINTER(C.c_ubyte)))
        output = Blob()
        library = C.WinDLL('crypt32', use_last_error=True)
        function = library.CryptUnprotectData if decrypt else library.CryptProtectData
        function.argtypes = [C.POINTER(Blob), C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p, W.DWORD, C.POINTER(Blob)]
        if not function(C.byref(incoming), None, None, None, None, 1, C.byref(output)):
            raise CalendarError('Não foi possível acessar as credenciais protegidas desta conta do Windows.')
        try:
            return C.string_at(output.data, output.size)
        finally:
            kernel = C.WinDLL('kernel32')
            kernel.LocalFree.argtypes = [C.c_void_p]
            kernel.LocalFree(output.data)

    def load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.crypt(self.path.read_bytes(), decrypt=True))

    def save(self, config):
        encoded = self.crypt(json.dumps(config, ensure_ascii=False).encode())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_bytes(encoded)
        temp.replace(self.path)

    def disconnect(self):
        self.path.unlink(missing_ok=True)


@dataclass
class Remote:
    uid: str
    href: str
    etag: str
    ics: str
    values: dict | None


def parse_event(ics):
    calendar = Calendar.from_ical(ics)
    events = calendar.walk('VEVENT')
    if not events:
        raise CalendarError('Evento sem componente de calendário.')
    event = events[0]
    uid = str(event.get('UID', ''))
    if not uid:
        raise CalendarError('Evento sem identificador.')
    # Never turn a series/invitation into a single event or modify its attendees.
    if len(events) != 1 or any(key in event for key in ('RRULE', 'RDATE', 'RECURRENCE-ID', 'ATTENDEE', 'ORGANIZER')):
        return uid, None
    if 'DTSTART' not in event:
        return uid, None
    start = event.decoded('DTSTART')
    end = event.decoded('DTEND') if 'DTEND' in event else None
    duration = event.decoded('DURATION') if 'DURATION' in event else None
    if end is None:
        end = start + (duration or (timedelta(minutes=30) if isinstance(start, datetime) else timedelta(days=1)))
    if isinstance(start, datetime):
        start = start.replace(tzinfo=ZONE) if start.tzinfo is None else start.astimezone(ZONE)
        end = end.replace(tzinfo=ZONE) if end.tzinfo is None else end.astimezone(ZONE)
        time = start.strftime('%H:%M')
    else:
        time = ''
    minutes = max(1, int((end - start).total_seconds() / 60))
    category = str(event.get('X-DIOLINO-CATEGORY', 'Compromisso'))
    if category not in ('Tarefa', 'Compromisso', 'Nota'):
        category = 'Compromisso'
    state = str(event.get('X-DIOLINO-STATE', 'Pendente'))
    if state not in ('Pendente', 'Concluído', 'Cancelado'):
        state = 'Pendente'
    if str(event.get('STATUS', '')) == 'CANCELLED':
        state = 'Cancelado'
    return uid, dict(date=start.strftime('%Y-%m-%d'), time=time, duration_min=minutes,
                     title=str(event.get('SUMMARY', 'Sem título')), category=category, state=state,
                     reminder='Sim' if time and event.subcomponents and any(c.name == 'VALARM' for c in event.subcomponents) else 'Não',
                     description=str(event.get('DESCRIPTION', '')))


def event_ics(row, uid, previous=None):
    calendar = Calendar.from_ical(previous) if previous else Calendar()
    if previous:
        parsed_uid, supported = parse_event(previous)
        if parsed_uid != uid or supported is None:
            raise CalendarError('Recorrências e convites devem ser editados no Calendário da Apple.')
        event = calendar.walk('VEVENT')[0]
        old_duration = supported['duration_min']
    else:
        calendar.add('PRODID', '-//Projeto Diolino//Agenda//PT-BR')
        calendar.add('VERSION', '2.0')
        event = Event()
        calendar.add_component(event)
        old_duration = 30
    all_day = not row.get('time')
    if all_day:
        start = date.fromisoformat(row['date'])
        duration = timedelta(days=max(1, int((row.get('duration_min') or 1440) / 1440)))
    else:
        start = datetime.fromisoformat(row['date'] + 'T' + row['time']).replace(tzinfo=ZONE).astimezone(timezone.utc)
        duration = timedelta(minutes=row.get('duration_min') or old_duration)
    for key in ('UID', 'DTSTART', 'DTEND', 'DURATION', 'SUMMARY', 'DESCRIPTION', 'STATUS', 'DTSTAMP', 'LAST-MODIFIED', 'X-DIOLINO-CATEGORY', 'X-DIOLINO-STATE'):
        event.pop(key, None)
    for key, value in [('UID', uid), ('DTSTART', start), ('DTEND', start + duration),
                       ('SUMMARY', row['title']), ('DESCRIPTION', row.get('description') or ''),
                       ('STATUS', 'CANCELLED' if row['state'] != 'Pendente' or row.get('deleted_at') else 'CONFIRMED'),
                       ('DTSTAMP', datetime.now(timezone.utc)), ('LAST-MODIFIED', datetime.now(timezone.utc)),
                       ('X-DIOLINO-CATEGORY', row['category']), ('X-DIOLINO-STATE', row['state'])]:
        event.add(key, value)
    event.subcomponents = [c for c in event.subcomponents if c.name != 'VALARM']
    if row.get('reminder') == 'Sim' and not all_day and row['state'] == 'Pendente' and not row.get('deleted_at'):
        alarm = Alarm()
        alarm.add('ACTION', 'DISPLAY')
        alarm.add('DESCRIPTION', row['title'])
        alarm.add('TRIGGER', timedelta(0))
        event.add_component(alarm)
    return calendar.to_ical().decode('utf-8')


class ICloudTransport:
    def __init__(self, username, password, calendar_url=None):
        import caldav
        if not username.strip() or not password.strip():
            raise CalendarError('Informe a Conta Apple e a senha específica de app no aplicativo.')
        # iCloud discovery returns a shard host (pXX-caldav.icloud.com).
        # CalDAV objects require the calendar and client to share that host.
        endpoint = icloud_url(calendar_url) if calendar_url else 'https://caldav.icloud.com/'
        self.client = caldav.DAVClient(url=endpoint, username=username.strip(),
                                       password=password.strip(), auth_type='basic', timeout=20,
                                       ssl_verify_cert=True, enable_rfc6764=False, require_tls=True, rate_limit_handle=False)
        self.calendar = caldav.Calendar(client=self.client, url=icloud_url(calendar_url)) if calendar_url else None

    def close(self):
        self.client.close()

    def calendars(self):
        return [dict(name=c.get_display_name() or 'Sem nome', url=icloud_url(c.url))
                for c in self.client.get_principal().calendars()]

    def create_calendar(self):
        matches = [c for c in self.calendars() if c['name'] == 'Projeto Diolino']
        if matches:
            return matches[0]
        calendar = self.client.get_principal().make_calendar(name='Projeto Diolino')
        return dict(name='Projeto Diolino', url=icloud_url(calendar.url))

    def fetch(self, href):
        response = self.client.request(icloud_url(href), method='GET')
        if response.status != 200:
            raise CalendarError('Não foi possível ler um evento do iCloud.')
        raw = response.raw
        raw = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
        uid, values = parse_event(raw)
        return Remote(uid, str(href), response.headers.get('ETag', ''), raw, values)

    def events(self):
        if self.calendar is None:
            raise CalendarError('Escolha o calendário antes de sincronizar.')
        result = {}
        for event in self.calendar.get_events():
            record = self.fetch(str(event.url))
            if record.uid in result:
                raise CalendarError('Há identificadores de eventos repetidos no calendário. Resolva isso no iCloud antes de sincronizar.')
            result[record.uid] = record
        return result

    def put(self, uid, ics, remote=None):
        if remote and not remote.etag:
            raise CalendarError('O iCloud não informou a versão do evento; a gravação foi interrompida para preservar alterações.')
        href = remote.href if remote else str(self.calendar.url).rstrip('/') + '/' + quote(uid, safe='') + '.ics'
        headers = {'Content-Type': 'text/calendar; charset=utf-8',
                   'If-Match' if remote else 'If-None-Match': remote.etag if remote else '*'}
        response = self.client.put(icloud_url(href), ics, headers=headers)
        if response.status in (409, 412):
            raise ConcurrentChange('O evento mudou no iCloud durante a sincronização. Tente novamente.')
        if response.status not in (200, 201, 204):
            raise CalendarError('O iCloud não aceitou a atualização do evento.')
        return self.fetch(href)


def expand_recurrences(remotes, today=None):
    """Read-only occurrences; the original Apple series is never uploaded back."""
    import recurring_ical_events
    today = today or datetime.now(ZONE).date()
    start, end = today - timedelta(days=366), today + timedelta(days=731)
    result = {}
    for uid, remote in remotes.items():
        if uid.startswith(SERIES_PREFIX):
            raise CalendarError('Identificador reservado encontrado no iCloud. A sincronização foi interrompida.')
        if remote.values is not None:
            result[uid] = remote
            continue
        calendar = Calendar.from_ical(remote.ics)
        events = calendar.walk('VEVENT')
        recurring = any(any(k in e for k in ('RRULE', 'RDATE', 'RECURRENCE-ID')) for e in events)
        if not recurring or any('ATTENDEE' in e or 'ORGANIZER' in e for e in events):
            result[uid] = remote
            continue
        query = recurring_ical_events.of(calendar)
        count = 0
        for event in query.after(start):
            when = event.decoded('DTSTART')
            day = when.astimezone(ZONE).date() if isinstance(when, datetime) and when.tzinfo else when.date() if isinstance(when, datetime) else when
            if day >= end:
                break
            count += 1
            if count > 5000:
                raise CalendarError('A série possui ocorrências demais no período de importação. Nenhum envio foi iniciado.')
            identity = event.decoded('RECURRENCE-ID') if 'RECURRENCE-ID' in event else when
            key = SERIES_PREFIX + fingerprint(uid) + ':' + fingerprint(identity.isoformat())
            for field in ('RRULE', 'RDATE', 'EXDATE', 'EXRULE', 'RECURRENCE-ID'):
                event.pop(field, None)
            event['UID'] = key
            single = Calendar()
            single.add_component(event)
            body = single.to_ical().decode('utf-8')
            _, values = parse_event(body)
            if values is None:
                raise CalendarError('Não foi possível interpretar uma ocorrência da série. Nenhum envio foi iniciado.')
            values['description'] = (values['description'] + '\n\nEvento recorrente do iCloud. Edite a série ou esta ocorrência no Calendário da Apple.').strip()
            result[key] = Remote(key, remote.href, remote.etag, body, values)
    return result, start, end


def sync_calendar(store, transport, calendar_key):
    """Three-way merge; stable UIDs and If-Match avoid duplicates/lost updates."""
    remotes, window_start, window_end = expand_recurrences(transport.events())
    links = {r['uid']: dict(r) for r in store.conn.execute('SELECT * FROM calendar_links WHERE calendar_key=?', (calendar_key,))}
    report = dict(sent=0, received=0, conflicts=0, unsupported=sum(r.values is None for r in remotes.values()))

    def save_link(uid, rid, local, remote, conflict=None, resolution=None):
        with store.conn:
            store.conn.execute('INSERT OR REPLACE INTO calendar_links(calendar_key,uid,agenda_id,href,etag,local_hash,remote_hash,base_ics,conflict,resolution) VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (calendar_key, uid, rid, remote.href if remote else None, remote.etag if remote else None,
                                fingerprint(local), fingerprint(remote.ics) if remote else 'deleted', remote.ics if remote else None, conflict, resolution))

    def receive(uid, row, values):
        store.conn.execute('BEGIN IMMEDIATE')
        current = dict(store.conn.execute('SELECT * FROM agenda WHERE id=?', (row['id'],)).fetchone())
        if fingerprint(current) != fingerprint(row):
            store.conn.execute('UPDATE calendar_links SET conflict=?,resolution=NULL WHERE calendar_key=? AND uid=?',
                               ('O item mudou no PC durante a sincronização. Escolha qual versão manter.', calendar_key, uid))
            store.conn.commit()
            report['conflicts'] += 1
            return None
        try:
            if current.get('deleted_at'):
                store.conn.execute('UPDATE agenda SET deleted_at=NULL WHERE id=?', (row['id'],))
                store.audit('agenda', row['id'], 'restaurar pelo iCloud', current, dict(current, deleted_at=None))
            store.save('agenda', values, row['id'])
            return store.get('agenda', row['id'])
        except Exception:
            store.conn.rollback()
            raise

    linked_ids = {link['agenda_id'] for link in links.values()}
    # These are local projections, not separate Apple events. Never PUT them.
    for uid in set(links) | set(remotes):
        if not uid.startswith(SERIES_PREFIX):
            continue
        link = links.pop(uid, None)
        remote = remotes.pop(uid, None)
        row = None
        if link:
            row = dict(store.conn.execute('SELECT * FROM agenda WHERE id=?', (link['agenda_id'],)).fetchone())
        values = remote.values if remote else None
        if not remote and row and window_start.isoformat() <= row['date'] < window_end.isoformat():
            values = dict(row, state='Cancelado', reminder='Não')
        if values is None:
            continue
        if row is None:
            rid = store.save('agenda', values)
            row = store.get('agenda', rid)
            report['received'] += 1
        elif fingerprint(row) != fingerprint(values):
            store.save('agenda', values, row['id'])
            row = store.get('agenda', row['id'])
            report['received'] += 1
        save_link(uid, row['id'], row, remote)
        linked_ids.add(row['id'])
    for row in store.rows('agenda'):
        if row['id'] in linked_ids or row['state'] != 'Pendente':
            continue
        uid = str(uuid.uuid4()) + '@diolino.local'
        # Save identity before network I/O; a retry reuses it after a lost response.
        with store.conn:
            store.conn.execute('INSERT INTO calendar_links(calendar_key,uid,agenda_id,local_hash,remote_hash) VALUES(?,?,?,?,?)',
                               (calendar_key, uid, row['id'], '', ''))
        links[uid] = dict(store.conn.execute('SELECT * FROM calendar_links WHERE calendar_key=? AND uid=?', (calendar_key, uid)).fetchone())

    for uid, link in links.items():
        raw = store.conn.execute('SELECT * FROM agenda WHERE id=?', (link['agenda_id'],)).fetchone()
        if raw is None:
            continue
        row = dict(raw)
        remote = remotes.get(uid)
        local_changed = fingerprint(row) != link['local_hash']
        remote_changed = (fingerprint(remote.ics) if remote else 'deleted') != link['remote_hash']
        resolution = link.get('resolution')
        conflict = None
        if remote and remote.values is None:
            conflict = 'Recorrência ou convite: edite este item no Calendário da Apple.'
        elif remote and not link['remote_hash'] and resolution not in ('local', 'remote'):
            _, expected = parse_event(event_ics(row, uid))
            if fingerprint(expected) == fingerprint(remote.values):
                save_link(uid, row['id'], row, remote)
                continue
            conflict = 'O envio anterior não foi confirmado e o iCloud contém outra versão. Escolha qual manter.'
        elif local_changed and remote_changed and link['remote_hash'] and resolution not in ('local', 'remote'):
            conflict = 'O item mudou no PC e no iCloud. Escolha qual versão manter.'
        if conflict:
            with store.conn:
                store.conn.execute('UPDATE calendar_links SET conflict=? WHERE calendar_key=? AND uid=?', (conflict, calendar_key, uid))
            report['conflicts'] += 1
            continue
        if resolution == 'remote' or (remote_changed and not local_changed and link['remote_hash']):
            if remote:
                row = receive(uid, row, remote.values)
            elif not row.get('deleted_at'):
                row = receive(uid, row, dict(row, state='Cancelado', reminder='Não'))
            if row is None:
                continue
            save_link(uid, row['id'], row, remote)
            report['received'] += 1
        elif local_changed or resolution == 'local' or not link['remote_hash']:
            if remote is None and link['remote_hash'] == 'deleted' and resolution != 'local':
                with store.conn:
                    store.conn.execute('UPDATE calendar_links SET conflict=? WHERE calendar_key=? AND uid=?', ('Item removido no iCloud; escolha Manter PC para recriá-lo.', calendar_key, uid))
                report['conflicts'] += 1
                continue
            # Do not resurrect a locally deleted event if its server copy is gone.
            if remote is None and row.get('deleted_at'):
                save_link(uid, row['id'], row, None)
                continue
            body = event_ics(row, uid, remote.ics if remote else None)
            try:
                saved = transport.put(uid, body, remote)
            except ConcurrentChange:
                report['conflicts'] += 1
                with store.conn:
                    store.conn.execute('UPDATE calendar_links SET conflict=?,resolution=NULL WHERE calendar_key=? AND uid=?', ('O iCloud mudou durante a gravação; sincronize novamente.', calendar_key, uid))
                continue
            save_link(uid, row['id'], row, saved)
            report['sent'] += 1
        elif remote_changed:
            save_link(uid, row['id'], row, remote)
    for uid, remote in remotes.items():
        if uid in links or remote.values is None:
            continue
        rid = store.save('agenda', remote.values)
        save_link(uid, rid, store.get('agenda', rid), remote)
        report['received'] += 1
    return report
