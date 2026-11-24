import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cloud_calendar import (Remote, PrivateSettings, ConcurrentChange, CalendarError, ICloudTransport,
                            event_ics, parse_event, sync_calendar, icloud_url, fingerprint, connection_error_message)
from storage import Store

KEY = 'https://p01-caldav.icloud.com/test/calendars/diolino/'


class TransportConstructionTests(unittest.TestCase):
    def test_error_messages_do_not_expose_remote_exception_body(self):
        secret = 'private-password-and-event-body'
        for name in ('ValueError', 'AuthorizationError', 'ConnectionError'):
            exc = type(name, (Exception,), {})(secret)
            self.assertNotIn(secret, connection_error_message(exc))
        self.assertIn('falha interna', connection_error_message(ValueError(secret)))

    def test_discovered_shard_builds_real_calendar_without_network(self):
        transport = ICloudTransport('synthetic@example.com', 'synthetic-password', KEY)
        try:
            self.assertEqual(str(transport.client.url), KEY)
            self.assertEqual(str(transport.calendar.url), KEY)
        finally:
            transport.close()

    def test_discovery_starts_at_apple_root(self):
        transport = ICloudTransport('synthetic@example.com', 'synthetic-password')
        try:
            self.assertEqual(str(transport.client.url), 'https://caldav.icloud.com/')
            self.assertIsNone(transport.calendar)
        finally:
            transport.close()


def agenda(**kwargs):
    return dict(date='2026-10-16', time='21:00', title='Estudar medicina',
                category='Tarefa', state='Pendente', reminder='Sim', description='Revisar conteúdo') | kwargs


class FakeCloud:
    def __init__(self):
        self.records = {}
        self.writes = 0
        self.lose_reply = False

    def events(self):
        return copy.deepcopy(self.records)

    def put(self, uid, ics, remote=None):
        current = self.records.get(uid)
        if (remote and (current is None or current.etag != remote.etag)) or (remote is None and current):
            raise ConcurrentChange('Concurrent update')
        self.writes += 1
        _, values = parse_event(ics)
        item = Remote(uid, KEY + uid + '.ics', f'"{self.writes}"', ics, values)
        self.records[uid] = item
        if self.lose_reply:
            self.lose_reply = False
            raise OSError('Reply lost after commit')
        return copy.deepcopy(item)

    def change(self, uid, **kwargs):
        old = self.records[uid]
        return self.put(uid, event_ics(dict(old.values, **kwargs), uid, old.ics), old)


class CalendarFormatTests(unittest.TestCase):
    def test_utc_timezone_unicode_duration_and_calendar_notice(self):
        ics = event_ics(agenda(title='Bíblia; estudo, revisão', duration_min=60), 'abc')
        self.assertIn('DTSTART:20261017T000000Z', ics)
        uid, row = parse_event(ics)
        self.assertEqual(uid, 'abc')
        self.assertEqual(row['date'], '2026-10-16')
        self.assertEqual(row['time'], '21:00')
        self.assertEqual(row['duration_min'], 60)
        self.assertEqual(row['title'], 'Bíblia; estudo, revisão')
        self.assertEqual(row['reminder'], 'Sim')
        self.assertIn('BEGIN:VALARM', ics)

    def test_all_day_cancelled_and_recurring_invitation_guard(self):
        ics = event_ics(agenda(time='', reminder='Não'), 'day')
        self.assertIn('DTSTART;VALUE=DATE:20261016', ics)
        self.assertEqual(parse_event(ics)[1]['time'], '')
        self.assertNotIn('VALARM', ics)
        cancelled = event_ics(agenda(state='Cancelado'), 'day')
        self.assertEqual(parse_event(cancelled)[1]['state'], 'Cancelado')
        for property in ('RRULE:FREQ=DAILY', 'ATTENDEE:mailto:test@example.com'):
            guarded = ics.replace('END:VEVENT', property + '\r\nEND:VEVENT')
            self.assertIsNone(parse_event(guarded)[1])
            with self.assertRaises(CalendarError):
                event_ics(agenda(), 'day', guarded)

    def test_icloud_host_validation(self):
        self.assertEqual(icloud_url(KEY), KEY)
        for bad in ('http://caldav.icloud.com/', 'https://icloud.com.evil.test/',
                    'https://name:password@caldav.icloud.com/', 'https://example.com/'):
            with self.assertRaises(CalendarError):
                icloud_url(bad)

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI')
    def test_secrets_are_encrypted_outside_database(self):
        with tempfile.TemporaryDirectory() as folder:
            vault = PrivateSettings(folder)
            config = dict(username='synthetic@example.com', password='fake-app-password')
            vault.save(config)
            self.assertNotIn(b'fake-app-password', vault.path.read_bytes())
            self.assertNotIn(b'synthetic@example.com', vault.path.read_bytes())
            self.assertEqual(vault.load(), config)
            vault.disconnect()
            self.assertEqual(vault.load(), {})


class CalendarSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.cloud = FakeCloud()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def sync(self):
        return sync_calendar(self.store, self.cloud, KEY)

    def first(self):
        rid = self.store.save('agenda', agenda())
        self.assertEqual(self.sync()['sent'], 1)
        return rid, next(iter(self.cloud.records))

    def test_idempotent_two_way_edit_and_duration_preserved(self):
        rid, uid = self.first()
        self.assertEqual(self.sync()['sent'], 0)
        self.assertEqual(len(self.cloud.records), 1)
        self.cloud.change(uid, title='Alterado no iPhone', duration_min=75)
        self.assertEqual(self.sync()['received'], 1)
        self.assertEqual(self.store.get('agenda', rid)['duration_min'], 75)
        self.store.save('agenda', agenda(title='Alterado no PC', duration_min=75), rid)
        self.assertEqual(self.sync()['sent'], 1)
        self.assertEqual(self.cloud.records[uid].values['title'], 'Alterado no PC')
        self.assertEqual(self.cloud.records[uid].values['duration_min'], 75)

    def test_import_does_not_duplicate_and_unsupported_is_skipped(self):
        self.cloud.put('external', event_ics(agenda(title='Criado na Apple'), 'external'))
        self.assertEqual(self.sync()['received'], 1)
        self.assertEqual(self.sync()['received'], 0)
        self.assertEqual(len(self.store.rows('agenda')), 1)
        recurring = event_ics(agenda(), 'recurring').replace('END:VEVENT', 'ATTENDEE:mailto:test@example.com\r\nEND:VEVENT')
        self.cloud.put('recurring', recurring)
        self.assertEqual(self.sync()['unsupported'], 1)
        self.assertEqual(len(self.store.rows('agenda')), 1)

    def test_yearly_series_imports_without_duplicates_or_remote_writes(self):
        body = event_ics(agenda(time='', reminder='Não', title='Aniversário'), 'birthday')
        body = body.replace('END:VEVENT', 'RRULE:FREQ=YEARLY\r\nEND:VEVENT')
        self.cloud.put('birthday', body)
        writes = self.cloud.writes
        report = self.sync()
        self.assertEqual(report['unsupported'], 0)
        self.assertGreaterEqual(report['received'], 2)
        self.assertEqual(self.sync()['received'], 0)
        self.assertEqual(self.cloud.writes, writes)
        original_ids = {r['id'] for r in self.store.rows('agenda')}
        self.cloud.records['birthday'].ics = body.replace('Aniversário', 'Aniversário atualizado')
        self.assertEqual(self.sync()['received'], len(original_ids))
        self.assertEqual({r['id'] for r in self.store.rows('agenda')}, original_ids)
        self.assertTrue(all(r['title'] == 'Aniversário atualizado' for r in self.store.rows('agenda')))
        del self.cloud.records['birthday']
        self.sync()
        self.assertTrue(all(r['state'] == 'Cancelado' for r in self.store.rows('agenda')))
        self.assertEqual(self.cloud.writes, writes)

    def test_series_exdate_and_moved_occurrence_keep_identity(self):
        body = ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:series\r\n'
                'DTSTART;VALUE=DATE:20261020\r\nDTEND;VALUE=DATE:20261021\r\n'
                'RRULE:FREQ=DAILY;COUNT=3\r\nEXDATE;VALUE=DATE:20261021\r\nSUMMARY:Serie\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')
        self.cloud.put('series', body)
        self.assertEqual(self.sync()['received'], 2)
        rows = {r['date']: r for r in self.store.rows('agenda')}
        exception = ('BEGIN:VEVENT\r\nUID:series\r\nRECURRENCE-ID;VALUE=DATE:20261022\r\n'
                     'DTSTART;VALUE=DATE:20261023\r\nDTEND;VALUE=DATE:20261024\r\nSUMMARY:Movido\r\nEND:VEVENT\r\n')
        self.cloud.records['series'].ics = body.replace('END:VCALENDAR', exception + 'END:VCALENDAR')
        self.sync()
        updated = {r['date']: r for r in self.store.rows('agenda')}
        self.assertEqual(updated['2026-10-23']['id'], rows['2026-10-22']['id'])
        self.assertEqual(updated['2026-10-23']['title'], 'Movido')

    def test_conflict_and_explicit_resolution(self):
        rid, uid = self.first()
        self.store.save('agenda', agenda(title='Versão PC'), rid)
        self.cloud.change(uid, title='Versão iPhone')
        self.assertEqual(self.sync()['conflicts'], 1)
        self.assertEqual(self.store.get('agenda', rid)['title'], 'Versão PC')
        self.assertEqual(self.cloud.records[uid].values['title'], 'Versão iPhone')
        with self.store.conn:
            self.store.conn.execute("UPDATE calendar_links SET resolution='remote'")
        self.assertEqual(self.sync()['received'], 1)
        self.assertEqual(self.store.get('agenda', rid)['title'], 'Versão iPhone')

    def test_local_and_remote_deletion_become_cancellations(self):
        rid, uid = self.first()
        self.store.delete('agenda', rid)
        self.assertEqual(self.sync()['sent'], 1)
        self.assertEqual(self.cloud.records[uid].values['state'], 'Cancelado')
        self.assertEqual(self.store.rows('agenda'), [])
        self.store.save('agenda', agenda(title='Outro'))
        self.sync()
        other = next(k for k in self.cloud.records if k != uid)
        del self.cloud.records[other]
        self.sync()
        self.assertEqual(self.store.rows('agenda')[0]['state'], 'Cancelado')
        self.assertEqual(self.sync()['sent'], 0)

    def test_lost_create_reply_reuses_uid(self):
        self.store.save('agenda', agenda())
        self.cloud.lose_reply = True
        with self.assertRaises(OSError):
            self.sync()
        self.assertEqual(len(self.cloud.records), 1)
        self.sync()
        self.assertEqual(len(self.cloud.records), 1)
        self.assertEqual(self.cloud.writes, 1)

    def test_conditional_write_conflict_and_network_failure_preserve_data(self):
        rid, uid = self.first()
        self.store.save('agenda', agenda(title='PC mais recente'), rid)
        with patch.object(self.cloud, 'put', side_effect=ConcurrentChange('changed')):
            self.assertEqual(self.sync()['conflicts'], 1)
        self.assertEqual(self.store.get('agenda', rid)['title'], 'PC mais recente')
        with patch.object(self.cloud, 'events', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                self.sync()
        self.assertEqual(self.store.get('agenda', rid)['state'], 'Pendente')

    def test_backup_restore_keeps_links_without_credentials(self):
        rid, uid = self.first()
        backup = self.store.backup()
        self.store.save('agenda', agenda(title='Outra versão'), rid)
        self.store.restore(backup)
        self.assertEqual(self.store.get('agenda', rid)['title'], 'Estudar medicina')
        self.assertEqual(self.store.conn.execute('SELECT uid FROM calendar_links').fetchone()[0], uid)

    def test_v5_migration_preserves_agenda_and_legacy_restore(self):
        rid = self.store.save('agenda', agenda())
        with self.store.conn:
            self.store.conn.execute('DROP TABLE calendar_links')
            self.store.conn.execute('ALTER TABLE agenda DROP COLUMN duration_min')
            self.store.conn.execute('PRAGMA user_version=5')
        legacy = self.store.backup()
        self.store.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.store.get('agenda', rid)['title'], 'Estudar medicina')
        self.assertIsNone(self.store.get('agenda', rid)['duration_min'])
        self.sync()
        self.store.restore(legacy)
        self.assertEqual(self.store.conn.execute('SELECT COUNT(*) FROM calendar_links').fetchone()[0], 0)
        self.assertEqual(self.store.get('agenda', rid)['title'], 'Estudar medicina')
