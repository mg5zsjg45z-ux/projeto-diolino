"""Local SQLite persistence, validation, audit trail, backups and CSV export."""
import csv
import io
import json
import math
import os
import sqlite3
import zipfile
import uuid
import unicodedata
import tempfile
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from models import MODELS, CHECK_GROUPS
from energy import energy_estimate
from nutrition import MACROS, SOURCE_NAME, validate_snapshot, scale, reference

SCHEMA_VERSION = 8


def default_directory():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ProjetoDiolino'


def number(value):
    return float(str(value).strip().replace(',', '.'))


def validate(kind, values):
    result = {}
    for f in MODELS[kind][1]:
        value = values.get(f.key)
        if isinstance(value, str):
            value = value.strip()
        if value in ('', None):
            if f.required:
                raise ValueError(f'Preencha: {f.label}.')
            result[f.key] = None
            continue
        try:
            if f.type in ('number', 'integer', 'workout', 'plan'):
                value = number(value)
                if not math.isfinite(value):
                    raise ValueError()
                if f.type in ('integer', 'workout', 'plan'):
                    if not value.is_integer():
                        raise ValueError()
                    value = int(value)
                if f.minimum is not None and value < f.minimum:
                    raise ValueError()
                if f.maximum is not None and value > f.maximum:
                    raise ValueError()
            elif f.type == 'date':
                value = date.fromisoformat(value).isoformat()
            elif f.type == 'time':
                value = datetime.strptime(value, '%H:%M').strftime('%H:%M')
            elif f.type == 'datetime':
                value = datetime.strptime(value, '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M')
            elif f.type == 'choice' and value not in f.choices:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f'Valor inválido em: {f.label}.') from None
        result[f.key] = value
    if kind == 'agenda' and result['reminder'] == 'Sim' and not result['time']:
        raise ValueError('Informe o horário do lembrete ou escolha Não em Notificar no Windows.')
    if kind == 'energy':
        energy_estimate(*(result[k] for k in ('weight_kg', 'height_cm', 'age_years', 'coefficient', 'activity_factor', 'deficit_pct')))
    if kind == 'sleep':
        start, end = (datetime.fromisoformat(result[k]) for k in ('start', 'end'))
        elapsed = (end - start).total_seconds() / 60
        if elapsed <= 0 or elapsed > 48 * 60:
            raise ValueError('O fim do sono deve ser posterior ao início, em um intervalo de até 48 horas.')
        if result['awake_min'] >= elapsed:
            raise ValueError('O tempo acordado deve ser menor que o intervalo de sono.')
        if result['date'] != end.date().isoformat():
            raise ValueError('A data do registro deve ser a data em que você acordou.')
    if kind == 'medication' and result['status'] == 'Tomado':
        if not result['taken_dose'] or not result['time']:
            raise ValueError('Para medicamento tomado, informe dose maior que zero e horário.')
    if kind == 'medication' and result['status'] != 'Tomado' and result['taken_dose']:
        raise ValueError('Uma dose tomada exige a situação Tomado.')
    if kind == 'body' and not any(result[k] is not None for k in ('weight_kg', 'waist_cm', 'hip_cm', 'chest_cm', 'arm_cm', 'thigh_cm', 'fat_pct')):
        raise ValueError('Informe pelo menos uma medida corporal.')
    if kind == 'plans' and result['start_date'] and result['end_date'] and result['end_date'] < result['start_date']:
        raise ValueError('O prazo do plano não pode ser anterior ao início.')
    return result


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else default_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'diolino.sqlite3'
        self.cache_epoch = 0
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('PRAGMA journal_mode=WAL')
        version = self.conn.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            self.conn.close()
            raise ValueError('Este banco foi criado por uma versão mais recente do aplicativo.')
        if 0 < version < SCHEMA_VERSION:
            self.backup()
        with self.conn:
            for kind, (_, fields) in MODELS.items():
                columns = []
                for f in fields:
                    sqltype = 'REAL' if f.type == 'number' else 'INTEGER' if f.type in ('integer', 'workout', 'plan') else 'TEXT'
                    clause = f'"{f.key}" {sqltype}' + (' NOT NULL' if f.required else '')
                    if f.type == 'workout':
                        clause += ' REFERENCES workout(id)'
                    if f.type == 'plan':
                        clause += ' REFERENCES plans(id)'
                    columns.append(clause)
                self.conn.execute(f'CREATE TABLE IF NOT EXISTS "{kind}" (id INTEGER PRIMARY KEY, {", ".join(columns)}, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT)')
                if any(f.key == 'date' for f in fields):
                    self.conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{kind}_date ON "{kind}"(date)')
            hydration_columns = {r[1] for r in self.conn.execute('PRAGMA table_info(hydration)')}
            if 'is_water' not in hydration_columns:
                self.conn.execute('ALTER TABLE hydration ADD COLUMN is_water TEXT')
            self.conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS daily_active_date ON daily(date) WHERE deleted_at IS NULL')
            self.conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS routine_active_date ON routine(date) WHERE deleted_at IS NULL')
            self.conn.execute('CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, entity TEXT, record_id INTEGER, action TEXT, timestamp TEXT, before_json TEXT, after_json TEXT)')
            self.conn.execute('CREATE TABLE IF NOT EXISTS agenda_notices (record_id INTEGER PRIMARY KEY, schedule TEXT NOT NULL, delivered_at TEXT NOT NULL)')
            self.conn.execute('CREATE TABLE IF NOT EXISTS food_nutrition (food_id INTEGER PRIMARY KEY REFERENCES food(id), snapshot_json TEXT NOT NULL)')
            if 'duration_min' not in {r[1] for r in self.conn.execute('PRAGMA table_info(agenda)')}:
                self.conn.execute('ALTER TABLE agenda ADD COLUMN duration_min INTEGER')
            self.conn.execute('CREATE TABLE IF NOT EXISTS calendar_links (calendar_key TEXT NOT NULL, uid TEXT NOT NULL, agenda_id INTEGER NOT NULL REFERENCES agenda(id), href TEXT, etag TEXT, local_hash TEXT, remote_hash TEXT, base_ics TEXT, conflict TEXT, resolution TEXT, PRIMARY KEY(calendar_key,uid), UNIQUE(calendar_key,agenda_id))')
            self.conn.execute('CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            self.conn.execute("CREATE TABLE IF NOT EXISTS notebook (id INTEGER PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, body TEXT NOT NULL, formatting TEXT NOT NULL DEFAULT '[]', labels TEXT NOT NULL DEFAULT '', favorite INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT)")
            self.conn.execute('CREATE INDEX IF NOT EXISTS notebook_date ON notebook(date)')
            self.conn.execute('CREATE TABLE IF NOT EXISTS bible_marks (version TEXT, book TEXT, chapter INTEGER, verse INTEGER, PRIMARY KEY(version,book,chapter,verse))')
            self.conn.execute(f'PRAGMA user_version={SCHEMA_VERSION}')

    def close(self):
        self.conn.close()

    def rows(self, kind, day=None):
        assert kind in MODELS
        sql = f'SELECT * FROM "{kind}" WHERE deleted_at IS NULL'
        args = []
        if day:
            if kind == 'sets':
                sql += ' AND workout_id IN (SELECT id FROM workout WHERE date=? AND deleted_at IS NULL)'
                args.append(day)
            elif any(f.key == 'date' for f in MODELS[kind][1]):
                sql += ' AND date=?'
                args.append(day)
        order = 'date DESC, id DESC' if any(f.key == 'date' for f in MODELS[kind][1]) else 'id DESC'
        return [dict(r) for r in self.conn.execute(sql + f' ORDER BY {order}', args)]

    def get(self, kind, rid):
        assert kind in MODELS
        row = self.conn.execute(f'SELECT * FROM "{kind}" WHERE id=? AND deleted_at IS NULL', (rid,)).fetchone()
        result = dict(row) if row else None
        if result and kind == 'food':
            source = self.conn.execute('SELECT snapshot_json FROM food_nutrition WHERE food_id=?', (rid,)).fetchone()
            result['_nutrition'] = json.loads(source[0]) if source else None
        return result

    def audit(self, kind, rid, action, before, after):
        self.conn.execute('INSERT INTO audit(entity,record_id,action,timestamp,before_json,after_json) VALUES(?,?,?,?,?,?)',
                          (kind, rid, action, datetime.now().isoformat(timespec='seconds'), json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False)))

    def save(self, kind, values, rid=None, nutrition=None, idempotency_key=None):
        snapshot_json = None
        if kind == 'food' and nutrition is not None:
            validate_snapshot(nutrition)
            if values.get('unit') != 'g':
                raise ValueError('A TACO calcula por gramas de parte comestível. Use g ou mude para preenchimento manual.')
            totals = scale(nutrition['food']['nutrients'], values.get('quantity'))
            values = dict(values, **{key: totals[key] for key in MACROS},
                          food_name=nutrition['food']['name'], source=SOURCE_NAME, reference=reference(nutrition))
            snapshot_json = json.dumps(dict(nutrition, grams=number(values['quantity'])), ensure_ascii=False, allow_nan=False)
        data = validate(kind, values)
        if kind == 'food' and data['source'] == SOURCE_NAME and nutrition is None:
            raise ValueError('Selecione o alimento no catálogo TACO ou mude a fonte para preenchimento manual.')
        if kind == 'sets' and not self.get('workout', data['workout_id']):
            raise ValueError('Selecione um treino ativo.')
        if kind == 'plan_steps' and not self.get('plans', data['plan_id']):
            raise ValueError('Selecione um plano existente e não excluído.')
        if kind == 'profile' and rid is None and self.rows('profile'):
            raise ValueError('Seu perfil já existe. Selecione-o e use Editar.')
        if kind in ('daily', 'routine'):
            existing = self.rows(kind, data['date'])
            if existing and existing[0]['id'] != rid:
                raise ValueError('Já existe um registro diário para esta data. Use Editar.')
        before = self.get(kind, rid) if rid else None
        if rid and not before:
            raise ValueError('Registro não encontrado.')
        now = datetime.now().isoformat(timespec='seconds')
        with self.conn:
            if idempotency_key:
                existing = self.conn.execute('SELECT value FROM preferences WHERE key=?',
                                             (idempotency_key,)).fetchone()
                if existing:
                    return int(existing[0])
            if rid:
                assignments = ', '.join(f'"{key}"=?' for key in data)
                self.conn.execute(f'UPDATE "{kind}" SET {assignments}, updated_at=? WHERE id=?', (*data.values(), now, rid))
            else:
                keys = ', '.join(f'"{key}"' for key in data)
                placeholders = ','.join('?' for _ in data)
                cursor = self.conn.execute(f'INSERT INTO "{kind}" ({keys},created_at,updated_at) VALUES({placeholders},?,?)', (*data.values(), now, now))
                rid = cursor.lastrowid
            if kind == 'food':
                if snapshot_json is not None:
                    self.conn.execute('INSERT OR REPLACE INTO food_nutrition(food_id,snapshot_json) VALUES(?,?)', (rid, snapshot_json))
                else:
                    self.conn.execute('DELETE FROM food_nutrition WHERE food_id=?', (rid,))
            self.audit(kind, rid, 'editar' if before else 'criar', before, self.get(kind, rid))
            if idempotency_key:
                self.conn.execute('INSERT INTO preferences(key,value) VALUES(?,?)',
                                  (idempotency_key, str(rid)))
        return rid

    def delete(self, kind, rid):
        before = self.get(kind, rid)
        if not before:
            raise ValueError('Registro não encontrado.')
        if kind == 'workout' and any(row['workout_id'] == rid for row in self.rows('sets')):
            raise ValueError('Este treino tem séries. Exclua as séries associadas primeiro.')
        if kind == 'plans' and any(row['plan_id'] == rid for row in self.rows('plan_steps')):
            raise ValueError('Este plano tem etapas. Use Arquivado para guardá-lo sem perder o histórico.')
        with self.conn:
            now = datetime.now().isoformat(timespec='seconds')
            self.conn.execute(f'UPDATE "{kind}" SET deleted_at=?, updated_at=? WHERE id=?', (now, now, rid))
            self.audit(kind, rid, 'excluir', before, None)

    def history(self, kind, rid):
        return [dict(r) for r in self.conn.execute('SELECT * FROM audit WHERE entity=? AND record_id=? ORDER BY id DESC', (kind, rid))]

    def backup(self, destination=None):
        if destination is None:
            folder = self.directory / 'backups'
            folder.mkdir(exist_ok=True)
            destination = folder / f'diolino-{datetime.now():%Y%m%d-%H%M%S-%f}-{uuid.uuid4().hex[:8]}.sqlite3'
        destination = Path(destination)
        if destination.resolve() == self.path.resolve():
            raise ValueError('Escolha um arquivo diferente do banco ativo.')
        with closing(sqlite3.connect(destination)) as target:
            self.conn.backup(target)
        return destination

    def daily_backup(self):
        folder = self.directory / 'backups'
        if not folder.exists() or not list(folder.glob(f'diolino-{datetime.now():%Y%m%d}-*.sqlite3')):
            self.backup()

    def restore(self, source):
        source = Path(source).resolve()
        if source == self.path.resolve():
            raise ValueError('Selecione um arquivo de backup, não o banco ativo.')
        incoming = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
        try:
            if incoming.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('O backup está corrompido.')
            version = incoming.execute('PRAGMA user_version').fetchone()[0]
            if version not in (1, 2, 3, 4, 5, 6, 7, SCHEMA_VERSION):
                raise ValueError('Versão de backup incompatível.')
            for kind, (_, fields) in MODELS.items():
                if version < 7 and kind in ('plans', 'plan_steps'):
                    continue
                if version < 4 and kind == 'agenda':
                    continue
                if version < 3 and kind == 'energy':
                    continue
                if version == 1 and kind == 'routine':
                    continue
                expected = {'id', 'created_at', 'updated_at', 'deleted_at'} | {f.key for f in fields}
                if version < 6 and kind == 'agenda':
                    expected.discard('duration_min')
                if version == 1 and kind == 'hydration':
                    expected.discard('is_water')
                actual = {r[1] for r in incoming.execute(f'PRAGMA table_info("{kind}")')}
                if not expected.issubset(actual):
                    raise ValueError('O arquivo não contém um banco completo do Projeto Diolino.')
            if incoming.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('O backup contém relações inválidas.')
            if not incoming.execute("SELECT name FROM sqlite_master WHERE name='audit'").fetchone():
                raise ValueError('Histórico ausente no backup.')
            if version >= 4:
                columns = {r[1] for r in incoming.execute('PRAGMA table_info(agenda_notices)')}
                if not {'record_id', 'schedule', 'delivered_at'}.issubset(columns):
                    raise ValueError('Registro de lembretes ausente no backup.')
            if version >= 5:
                columns = {r[1] for r in incoming.execute('PRAGMA table_info(food_nutrition)')}
                if not {'food_id', 'snapshot_json'}.issubset(columns):
                    raise ValueError('Referências nutricionais ausentes no backup.')
            if version >= 6:
                expected_links = {'calendar_key', 'uid', 'agenda_id', 'href', 'etag', 'local_hash', 'remote_hash', 'base_ics', 'conflict', 'resolution'}
                if not expected_links.issubset({r[1] for r in incoming.execute('PRAGMA table_info(calendar_links)')}):
                    raise ValueError('Vínculos do calendário ausentes no backup.')
            if version >= 8:
                for table, expected in {
                    'notebook': {'id','title','date','body','formatting','labels','favorite','created_at','updated_at','deleted_at'},
                    'preferences': {'key','value'},
                    'bible_marks': {'version','book','chapter','verse'},
                }.items():
                    if not expected.issubset({r[1] for r in incoming.execute(f'PRAGMA table_info("{table}")')}):
                        raise ValueError('Backup incompleto: ' + table)
            # Upgrade a disposable copy before replacing the live database.
            with tempfile.TemporaryDirectory() as folder:
                with closing(sqlite3.connect(Path(folder) / 'diolino.sqlite3')) as staged:
                    incoming.backup(staged)
                migrated = Store(folder)
                try:
                    safety = self.backup()
                    migrated.conn.backup(self.conn)
                    self.cache_epoch += 1
                finally:
                    migrated.close()
            return safety
        finally:
            incoming.close()

    def export(self, destination):
        def safe(value):
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                return "'" + value
            return value
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for kind in [*MODELS, 'audit', 'agenda_notices', 'food_nutrition', 'calendar_links', 'notebook', 'preferences', 'bible_marks']:
                sort_key = 'key' if kind == 'preferences' else 'version,book,chapter,verse' if kind == 'bible_marks' else 'calendar_key,uid' if kind == 'calendar_links' else 'food_id' if kind == 'food_nutrition' else 'record_id' if kind == 'agenda_notices' else 'id'
                cursor = self.conn.execute(f'SELECT * FROM "{kind}" ORDER BY {sort_key}')
                out = io.StringIO(newline='')
                writer = csv.writer(out, delimiter=';')
                writer.writerow([c[0] for c in cursor.description])
                writer.writerows([[safe(v) for v in row] for row in cursor])
                bundle.writestr(kind + '.csv', '\ufeff' + out.getvalue())
            bundle.writestr('LEIA-ME.txt', 'Projeto Diolino — exportação completa. CSV UTF-8 com separador ponto e vírgula.\nDatas ISO; valores decimais com ponto. deleted_at preenchido indica exclusão lógica.\nValores nutricionais são da quantidade consumida. Ausência de valor significa desconhecido.\nRestauração do aplicativo usa o backup SQLite, não este ZIP.\n')

    def summary(self, day):
        studies, workouts = self.rows('study', day), self.rows('workout', day)
        foods, sleeps = self.rows('food', day), self.rows('sleep', day)
        sleep_min = sum((datetime.fromisoformat(r['end']) - datetime.fromisoformat(r['start'])).total_seconds() / 60 - r['awake_min'] for r in sleeps)
        return {
            'study_min': sum(r['duration_min'] for r in studies), 'study_count': len(studies),
            'exercise_min': sum(r['duration_min'] for r in workouts), 'exercise_count': len(workouts),
            'bible_count': len(self.rows('bible', day)),
            'kcal': sum(r['kcal'] or 0 for r in foods), 'food_count': len(foods),
            'unknown_kcal': sum(r['kcal'] is None for r in foods),
            'estimated_foods': sum(r['source'] == 'Estimativa' for r in foods),
            'protein_g': sum(r['protein_g'] or 0 for r in foods),
            'sleep_min': sleep_min, 'sleep_count': len(sleeps),
            'water_ml': self.water_total(day),
            'daily': next(iter(self.rows('daily', day)), None),
        }

    def water_total(self, day):
        def is_water(row):
            if row.get('is_water') is not None:
                return row['is_water'] == 'Sim'
            # Conservative fallback for old records; other names require confirmation.
            name = ''.join(c for c in unicodedata.normalize('NFD', row['drink'].strip().casefold())
                           if not unicodedata.combining(c))
            return name in {'agua', 'agua mineral', 'agua filtrada', 'agua sem gas', 'agua com gas'}
        return sum(row['volume_ml'] for row in self.rows('hydration', day) if is_water(row))

    def latest_measurement(self, day, key='weight_kg'):
        rows = [r for r in self.rows('body') if r.get(key) is not None and r['date'] <= day]
        return max(rows, key=lambda r: (r['date'], r['time'] or '', r['id'])) if rows else None

    def upcoming_agenda(self, day):
        rows = [r for r in self.rows('agenda') if r['state'] == 'Pendente' and r['date'] >= day]
        return sorted((r | {'start': r['date'] + ' ' + (r['time'] or '--:--')} for r in rows), key=lambda r: (r['date'], r['time'] or '23:59', r['id']))

    def due_reminders(self, now):
        notices = {r['record_id']: r['schedule'] for r in self.conn.execute('SELECT * FROM agenda_notices')}
        due = []
        for row in self.rows('agenda'):
            schedule = row['date'] + ' ' + (row['time'] or '')
            if row['state'] == 'Pendente' and row['reminder'] == 'Sim' and row['time'] and schedule <= now.strftime('%Y-%m-%d %H:%M') and notices.get(row['id']) != schedule:
                due.append(row)
        return sorted(due, key=lambda r: (r['date'], r['time'], r['id']))

    def mark_notified(self, row, now):
        with self.conn:
            self.conn.execute('INSERT OR REPLACE INTO agenda_notices(record_id,schedule,delivered_at) VALUES(?,?,?)',
                              (row['id'], row['date'] + ' ' + row['time'], now.isoformat(timespec='seconds')))

    def body_series(self, key, start, end):
        rows = [r for r in self.rows('body') if r.get(key) is not None and start <= r['date'] <= end]
        points = {}
        for row in sorted(rows, key=lambda r: (r['date'], r['time'] or '', r['id'])):
            points[row['date']] = row[key]
        return sorted(points.items())

    def pillar_states(self, day):
        summary = self.summary(day)
        daily = summary['daily'] or {}
        result = {}
        for key, minutes, count, goal in [
            ('medicine_status', summary['study_min'], summary['study_count'], 60),
            ('exercise_status', summary['exercise_min'], summary['exercise_count'], 40),
            ('bible_status', summary['bible_count'], summary['bible_count'], 1),
        ]:
            explicit = daily.get(key, 'Não informado')
            if explicit != 'Não informado':
                result[key] = {'done': explicit == 'Realizado', 'source': 'Seu relato: ' + explicit, 'known': True}
            else:
                result[key] = {'done': minutes >= goal, 'source': 'Pelos registros' if count else 'Sem registro', 'known': bool(count)}
        return result

    def set_pillar(self, day, key, checked):
        if key not in ('medicine_status', 'exercise_status', 'bible_status'):
            raise ValueError('Pilar inválido.')
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            record = next(iter(self.rows('daily', day)), None)
            values = dict(record or {'date': day, 'shift': 'Não informado', 'medicine_status': 'Não informado',
                                     'exercise_status': 'Não informado', 'bible_status': 'Não informado'})
            values[key] = 'Realizado' if checked else 'Não realizado'
            return self.save('daily', values, record['id'] if record else None)
        except Exception:
            self.conn.rollback()
            raise

    def checklist(self, day):
        date.fromisoformat(day)
        record = next(iter(self.rows('routine', day)), None)
        weights = [r for r in self.rows('body') if r['weight_kg'] is not None and r['date'] <= day]
        weight = max(weights, key=lambda r: (r['date'], r['time'] or '', r['id'])) if weights else None
        target = weight['weight_kg'] * 50 if weight else None
        consumed = self.water_total(day)
        return {'record': record, 'weight': weight, 'water_target_ml': target, 'water_ml': consumed,
                'water_complete': target is not None and consumed >= target,
                'counts': {label: sum((record or {}).get(key) == 1 for key in keys) for label, keys in CHECK_GROUPS}}

    def set_check(self, day, key, checked):
        if key not in {k for _, keys in CHECK_GROUPS for k in keys}:
            raise ValueError('Item de checagem inválido.')
        if checked not in (0, 1, False, True):
            raise ValueError('Marque ou desmarque o item.')
        # A transaction prevents two windows from losing each other's check marks.
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            record = next(iter(self.rows('routine', day)), None)
            values = dict(record or {'date': day})
            values[key] = int(checked)
            return self.save('routine', values, record['id'] if record else None)
        except Exception:
            self.conn.rollback()
            raise
