import tempfile
import time
import unittest
from unittest.mock import patch
from tkinter import font

from app import App
from models import MODELS
from storage import Store
from table_layout import fit_columns


class TableCloudUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = App(Store(self.temp.name))
        self.app.withdraw()

    def tearDown(self):
        self.app.update()
        self.app.shutdown()
        self.temp.cleanup()

    def test_columns_follow_headers_contents_and_numeric_alignment(self):
        self.app.store.save('food', dict(date='2026-10-16', meal='Almoço', food_name='Arroz integral, cozido',
                                         quantity=150.5, unit='g', kcal=185.9, source='Rótulo'))
        self.app.day.set('2026-10-16')
        self.app.navigate('food')
        self.app.update_idletasks()
        fit_columns(self.app.tree, MODELS['food'][1])
        heading = font.Font(self.app.tree, font=('Segoe UI Semibold', 10))
        for col in self.app.tree['columns']:
            self.assertGreaterEqual(self.app.tree.column(col, 'width'), heading.measure(self.app.tree.heading(col, 'text')) + 30)
        self.assertEqual(str(self.app.tree.column('kcal', 'anchor')), 'e')
        self.assertEqual(self.app.tree.heading('protein_g', 'text'), 'Proteínas (g)')
        self.assertTrue(hasattr(self.app.tree, 'cell_preview'))

    def test_connection_never_activates_or_contacts_server_without_user_input(self):
        with patch('icloud_ui.ICloudTransport') as transport:
            self.app.navigate('icloud')
            self.app.cloud_connect('list')
            self.app.cloud_enable()
            self.app.check_cloud_schedule()
            transport.assert_not_called()
        self.assertFalse(self.app.cloud_config.get('enabled'))
        self.assertFalse(self.app.cloud_vault.path.exists())

    def test_discovery_requires_explicit_calendar_activation(self):
        class FakeTransport:
            def __init__(self, *args, **kwargs): pass
            def calendars(self): return [dict(name='Projeto Diolino', url='https://p01-caldav.icloud.com/test/calendar/')]
            def close(self): pass
        self.app.navigate('icloud')
        self.app.cloud_username.set('synthetic@example.com')
        self.app.cloud_password.set('fake-app-password')
        with patch('icloud_ui.ICloudTransport', FakeTransport):
            self.app.cloud_connect('list')
            deadline = time.monotonic() + 3
            while self.app.cloud_busy and time.monotonic() < deadline:
                self.app.update()
                time.sleep(.01)
        self.assertFalse(self.app.cloud_busy)
        self.assertEqual(self.app.cloud_username.get(), 'synthetic@example.com')
        self.assertEqual(self.app.cloud_password.get(), '')
        self.assertIn('Projeto Diolino', self.app.cloud_choices)
        self.assertFalse(self.app.cloud_config.get('enabled'))
        self.assertFalse(self.app.cloud_vault.path.exists())
