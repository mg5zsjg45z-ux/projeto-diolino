from http.cookiejar import CookieJar
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from mobile_server import MobileServer
from storage import Store


class MobileServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='test-output')
        self.server = MobileServer(('127.0.0.1', 0), self.temp.name, '123456789012')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(CookieJar()))
        self.csrf = ''

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, headers=None):
        headers = dict(headers or {})
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers.update({'Content-Type': 'application/json', 'X-CSRF-Token': self.csrf})
        req = urllib.request.Request(self.base + path, data=body, headers=headers)
        try:
            with self.client.open(req) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, json.load(response)

    def login(self):
        code, result = self.request('/api/login', {'code': '123456-789012'})
        self.assertEqual(code, 200)
        self.csrf = result['csrf']

    def test_no_health_data_without_login_and_bruteforce_limited(self):
        self.assertEqual(self.request('/api/overview')[0], 401)
        for _ in range(5):
            self.assertEqual(self.request('/api/login', {'code': 'wrong'})[0], 401)
        self.assertEqual(self.request('/api/login', {'code': '123456789012'})[0], 429)

    def test_same_sqlite_validation_csrf_and_checks(self):
        self.login()
        body = {'kind': 'body', 'values': {'date': '2026-10-16', 'weight_kg': 82.4}}
        correct = self.csrf
        self.csrf = 'invalid'
        self.assertEqual(self.request('/api/save', body)[0], 403)
        self.csrf = correct
        self.assertEqual(self.request('/api/save', body, {'Origin': 'http://evil.test'})[0], 403)
        self.assertEqual(self.request('/api/save', body)[0], 200)
        store = Store(self.temp.name)
        self.assertEqual(store.rows('body')[0]['weight_kg'], 82.4)
        store.close()
        self.assertEqual(self.request('/api/check', {'day': '2026-10-16', 'key': 'brush_1', 'checked': True})[0], 200)
        status, result = self.request('/api/overview?day=2026-10-16')
        self.assertEqual(status, 200)
        self.assertEqual(result['checks']['record']['brush_1'], 1)
        self.assertEqual(result['checks']['water_target_ml'], 4120)

    def test_host_guard_schema_taco_and_invalid_writes(self):
        self.assertEqual(self.request('/health', headers={'Host': 'evil.test'})[0], 403)
        self.login()
        self.assertIn('study', self.request('/api/schema')[1])
        self.assertGreater(len(self.request('/api/taco?q=arroz')[1]), 0)
        self.assertEqual(self.request('/api/save', {'kind': 'body', 'values': {'date': '2026-10-16', 'weight_kg': -1}})[0], 400)
        self.assertEqual(self.request('/api/save', {'kind': 'sqlite_master', 'values': {}})[0], 400)

    def test_removed_assistant_endpoints_are_unavailable(self):
        self.login()
        self.assertEqual(self.request('/api/interpret', {'text':'teste'})[0], 404)
        self.assertEqual(self.request('/api/audio', {})[0], 404)
        self.assertEqual(self.request('/api/job?id=removed')[0], 404)

    def test_plans_create_check_and_duplicate_share_database(self):
        self.login()
        status, result = self.request('/api/plans/create', {'values': {'title': 'Minha semana', 'area': 'Pessoal', 'status': 'Ativo', 'priority': 'Normal'}, 'steps': ['Primeiro passo']})
        self.assertEqual(status, 200)
        status, result = self.request('/api/plans?day=2026-10-16')
        self.assertEqual(result['plans'][0]['progress'], 0)
        step = result['plans'][0]['steps'][0]
        self.assertEqual(self.request('/api/plans/check', {'id': step['id'], 'checked': True})[0], 200)
        result = self.request('/api/plans?day=2026-10-16')[1]
        self.assertEqual(result['plans'][0]['progress'], 100)
        self.assertEqual(self.request('/api/plans/duplicate', {'id': result['plans'][0]['id']})[0], 200)
        self.assertEqual(len(self.request('/api/plans')[1]['plans']), 2)
