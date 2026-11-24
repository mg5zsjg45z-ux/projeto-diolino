import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from storage import Store
from manual_sync import apply_file, preview, snapshot
from site_sync import (SITE_URL, ConnectionVault, SyncError, SyncConflict, SiteClient,
                       export_data, synchronize, validate_connection, NoRedirect)


class Remote:
    def __init__(self, store):
        self.store, self.revision, self.writes, self.lose_response = store, 0, 0, False

    def request(self, data=None):
        file = export_data(self.store)
        file['exported_at'] = datetime.now(timezone.utc).isoformat()
        result = {'file': file, 'revision': self.revision, 'device_id': 'fixture-device-id-12345'}
        if data is None:
            return result
        plan = preview(self.store, data['file'])
        if data['action'] == 'preview':
            return {**result, 'conflicts': plan['conflicts'], 'counts': plan['counts']}
        if data['revision'] != self.revision:
            raise SyncError('stale')
        apply_file(self.store, data['file'], plan['base'], data['choices'])
        self.revision += 1; self.writes += 1
        if self.lose_response:
            self.lose_response = False
            raise SyncError('Response lost after server commit')
        return {'file': export_data(self.store), 'revision': self.revision, 'device_id': 'fixture-device-id-12345'}


class SiteSyncTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir='test-output')
        self.root = Path(self.folder.name)
        self.local, self.remote = Store(self.root/'pc'), Store(self.root/'site')
        self.client = Remote(self.remote)
        self.device = 'fixture-device-id-12345'

    def tearDown(self):
        self.local.close(); self.remote.close(); self.folder.cleanup()

    def study(self, store, title='Synthetic study', minutes=25, rid=None):
        return store.save('study', {'date':'2026-11-04','topic':title,'duration_min':minutes,'format':'Leitura'}, rid)

    def sync(self, **kwargs):
        return synchronize(self.local, self.client, self.device, **kwargs)

    def settle(self):
        for _ in range(3): self.sync()

    def test_colliding_ids_and_plan_relations_roundtrip_without_duplicates(self):
        self.study(self.local, 'PC'); self.study(self.remote, 'Site')
        for store, title in [(self.local, 'PC plan'), (self.remote, 'Site plan')]:
            rid = store.save('plans', {'title':title,'area':'Medicina','status':'Ativo','priority':'Normal'})
            store.save('plan_steps', {'plan_id':rid,'title':title+' step','state':'A fazer','priority':'Normal'})
        result = self.sync()
        self.assertTrue(Path(result['backup']).exists())
        self.settle()
        for store in (self.local, self.remote):
            self.assertEqual(len(store.rows('study')), 2)
            self.assertEqual(len(store.rows('plan_steps')), 2)
            for step in store.rows('plan_steps'):
                self.assertEqual(step['title'], store.get('plans', step['plan_id'])['title']+' step')

    def test_unilateral_changes_flow_both_ways_and_settled_pass_does_not_write(self):
        self.study(self.local); self.settle()
        self.study(self.remote, minutes=40, rid=self.remote.rows('study')[0]['id'])
        self.sync(); self.assertEqual(self.local.rows('study')[0]['duration_min'], 40)
        self.study(self.local, minutes=60, rid=self.local.rows('study')[0]['id'])
        self.sync(); self.assertEqual(self.remote.rows('study')[0]['duration_min'], 60)
        self.settle(); writes = self.client.writes
        self.sync(); self.sync()
        self.assertEqual(self.client.writes, writes)

    def change_both(self):
        self.study(self.local); self.settle()
        self.study(self.local, minutes=35, rid=self.local.rows('study')[0]['id'])
        self.study(self.remote, minutes=50, rid=self.remote.rows('study')[0]['id'])

    def conflict(self):
        with self.assertRaises(SyncConflict) as error:
            self.sync()
        return error.exception

    def test_concurrent_edit_is_preserved_until_explicit_local_choice(self):
        self.change_both(); pending = self.conflict()
        self.assertEqual(self.local.rows('study')[0]['duration_min'], 35)
        self.assertEqual(self.remote.rows('study')[0]['duration_min'], 50)
        self.sync(overrides={pending.conflicts[0]['choice_key']:'keep'}, expected_base=pending.base, expected_revision=pending.revision)
        self.assertEqual(self.remote.rows('study')[0]['duration_min'], 35)

    def test_explicit_online_choice_and_stale_approval(self):
        self.change_both(); pending = self.conflict()
        self.study(self.local, minutes=36, rid=self.local.rows('study')[0]['id'])
        with self.assertRaises(SyncError):
            self.sync(overrides={pending.conflicts[0]['choice_key']:'incoming'}, expected_base=pending.base, expected_revision=pending.revision)
        self.assertEqual(self.remote.rows('study')[0]['duration_min'], 50)
        pending = self.conflict()
        self.sync(overrides={pending.conflicts[0]['choice_key']:'incoming'}, expected_base=pending.base, expected_revision=pending.revision)
        self.assertEqual(self.local.rows('study')[0]['duration_min'], 50)

    def test_first_connection_differences_are_not_guessed(self):
        self.study(self.local, minutes=20); self.study(self.remote, minutes=60)
        self.assertEqual(len(self.conflict().conflicts), 1)
        self.assertEqual(self.local.rows('study')[0]['duration_min'], 20)

    def test_retry_after_lost_response_is_idempotent(self):
        self.study(self.local)
        self.client.lose_response = True
        with self.assertRaises(SyncError): self.sync()
        self.settle()
        self.assertEqual(len(self.local.rows('study')), 1)
        self.assertEqual(len(self.remote.rows('study')), 1)

    def test_deleted_rows_are_neither_resurrected_nor_propagated(self):
        rid = self.study(self.local); self.settle()
        self.local.delete('study', rid)
        result = self.sync()
        self.assertEqual(result['blocked'], 1)
        self.assertEqual(len(self.local.rows('study')), 0)
        self.assertEqual(len(self.remote.rows('study')), 1)

    def test_connection_is_dpapi_protected_and_not_in_database(self):
        config = {'format':'diolino-site-connection-1','url':SITE_URL,'device_id':self.device,
                  'device_token':'a'*64,'gateway_token':'synthetic-dispatch-token-12345',
                  'account':'synthetic@example.com','expires_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
        self.assertEqual(validate_connection(config), config)
        vault = ConnectionVault(self.root)
        vault.save(config)
        self.assertEqual(vault.load(), config)
        self.assertNotIn(config['gateway_token'].encode(), vault.path.read_bytes())
        self.assertNotIn(config['device_token'], json.dumps(export_data(self.local)))
        for key, bad in [('url','http://127.0.0.1:8765'), ('url',SITE_URL+'.evil.test'), ('device_token','a'*63+'\n'), ('expires_at','2000-01-01T00:00:00Z')]:
            with self.assertRaises(SyncError): validate_connection({**config,key:bad})
        client = SiteClient(config)
        self.assertTrue(client.opener.handlers[0] is not None)
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test'))
        vault.disconnect(); self.assertEqual(vault.load(), {})
