import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from storage import Store, SCHEMA_VERSION


class ChecklistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.day = '2026-10-16'

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_checks_survive_reopen_and_are_independent_by_day(self):
        self.store.set_check(self.day, 'brush_1', True)
        self.store.set_check(self.day, 'brush_3', True)
        self.store.set_check(self.day, 'bath_2', True)
        self.store.set_check(self.day, 'med_1', True)
        self.store.set_check(self.day, 'brush_1', False)
        self.store.close()
        self.store = Store(self.tmp.name)
        state = self.store.checklist(self.day)
        self.assertEqual(state['counts']['Higiene bucal'], 1)
        self.assertEqual(state['counts']['Banho'], 1)
        self.assertEqual(state['counts']['Checagem da medicação'], 1)
        self.assertEqual(len(self.store.rows('routine')), 1)
        self.assertEqual(len(self.store.history('routine', state['record']['id'])), 5)
        self.assertIsNone(self.store.checklist('2026-10-17')['record'])
        self.assertEqual(self.store.rows('medication'), [])
        self.assertEqual(self.store.rows('daily'), [])

    def test_water_uses_historical_weight_and_only_water(self):
        self.store.save('body', {'date': '2026-10-14', 'weight_kg': 70})
        self.store.save('body', {'date': self.day, 'time': '09:00', 'weight_kg': 80})
        self.store.save('body', {'date': self.day, 'time': '07:00', 'weight_kg': 75})
        self.store.save('body', {'date': '2026-10-17', 'weight_kg': 90})
        for name, volume, flag in [('Café', 300, None), ('Água', 1500, None), ('Água de coco', 1000, None), ('Garrafa', 2500, 'Sim'), ('Água', 600, 'Não')]:
            self.store.save('hydration', {'date': self.day, 'drink': name, 'volume_ml': volume, 'is_water': flag})
        state = self.store.checklist(self.day)
        self.assertEqual(state['water_target_ml'], 4000)
        self.assertEqual(state['water_ml'], 4000)
        self.assertTrue(state['water_complete'])
        self.assertEqual(self.store.checklist('2026-10-15')['water_target_ml'], 3500)
        self.assertIsNone(self.store.checklist('2026-10-13')['water_target_ml'])
        self.assertFalse(self.store.checklist('2026-10-13')['water_complete'])

    def test_checklist_backup_export_and_validation(self):
        for key in ('brush_1', 'brush_2', 'brush_3', 'bath_1', 'bath_2', 'med_1', 'med_2'):
            self.store.set_check(self.day, key, True)
        with self.assertRaises(ValueError):
            self.store.set_check(self.day, 'bad', True)
        with self.assertRaises(ValueError):
            self.store.save('routine', {'date': '2026-10-17', 'brush_1': 3})
        backup = self.store.backup()
        self.store.set_check(self.day, 'med_2', False)
        self.store.restore(backup)
        self.assertEqual(self.store.checklist(self.day)['counts']['Checagem da medicação'], 2)
        out = Path(self.tmp.name) / 'checklist.zip'
        self.store.export(out)
        with zipfile.ZipFile(out) as bundle:
            self.assertIn('routine.csv', bundle.namelist())
            self.assertIn(self.day, bundle.read('routine.csv').decode('utf-8-sig'))

    def test_upgrade_v1_preserves_data_and_restores_legacy_backup(self):
        self.store.save('body', {'date': self.day, 'weight_kg': 80})
        self.store.save('hydration', {'date': self.day, 'drink': 'Água', 'volume_ml': 500})
        self.store.conn.execute('DROP TABLE routine')
        self.store.conn.execute('ALTER TABLE hydration DROP COLUMN is_water')
        self.store.conn.execute('PRAGMA user_version=1')
        self.store.conn.commit()
        legacy = self.store.backup(Path(self.tmp.name) / 'legacy.sqlite3')
        self.store.close()
        self.store = Store(self.tmp.name)
        self.assertEqual(self.store.conn.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
        self.assertEqual(self.store.checklist(self.day)['water_ml'], 500)
        self.assertEqual(self.store.checklist(self.day)['water_target_ml'], 4000)
        backups = list((Path(self.tmp.name) / 'backups').glob('*.sqlite3'))
        self.assertTrue(backups)
        with closing(sqlite3.connect(backups[-1])) as backup:
            self.assertEqual(backup.execute('PRAGMA user_version').fetchone()[0], 1)
        self.store.set_check(self.day, 'bath_1', True)
        self.store.restore(legacy)
        self.assertIsNone(self.store.checklist(self.day)['record'])
        self.assertEqual(self.store.checklist(self.day)['water_ml'], 500)
        self.store.set_check(self.day, 'brush_1', True)
        self.assertEqual(self.store.checklist(self.day)['counts']['Higiene bucal'], 1)


if __name__ == '__main__':
    unittest.main()
