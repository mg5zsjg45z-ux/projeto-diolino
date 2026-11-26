import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from storage import Store
spec = importlib.util.spec_from_file_location('v3_bridge',ROOT/'desktop-v3'/'bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class BridgeTests(unittest.TestCase):
    def test_real_snapshot_and_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            try:
                store.save('study',{'date':'2026-11-25','topic':'Teste sintético','duration_min':45,'format':'Leitura'})
                path = store.path
            finally:
                store.close()
            before = path.read_bytes()
            data = bridge.snapshot(path,'2026-11-25',7)
            self.assertEqual(data['today']['study'],45)
            self.assertIsNone(data['today']['sleep'])
            self.assertEqual(data['series']['study'],[('2026-11-25',45)])
            self.assertEqual(path.read_bytes(),before)
    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'absent.sqlite3'
            with self.assertRaises(sqlite3.OperationalError):
                bridge.snapshot(path,'2026-11-25',7)
            self.assertFalse(path.exists())
    def test_period_and_schema_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'older.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.execute('PRAGMA user_version=0')
            with self.assertRaises(ValueError):
                bridge.snapshot(path,'2026-11-25',7)
            with self.assertRaises(ValueError):
                bridge.snapshot(path,'2026-11-25',8)
