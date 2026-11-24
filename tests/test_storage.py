import tempfile
import unittest
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path
from storage import Store, validate


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def study(self, minutes=30):
        return {'date': '2026-10-16', 'topic': 'Anatomia', 'duration_min': minutes, 'format': 'Leitura'}

    def workout(self):
        return self.store.save('workout', {'date': '2026-10-16', 'name': 'Treino A', 'modality': 'Musculação', 'duration_min': 40})

    def test_accumulation_and_missing_not_zero(self):
        self.assertEqual(self.store.summary('2026-10-16')['study_count'], 0)
        self.store.save('study', self.study(25))
        self.store.save('study', self.study(35))
        self.workout()
        s = self.store.summary('2026-10-16')
        self.assertEqual(s['study_min'], 60)
        self.assertEqual(s['exercise_min'], 40)
        self.assertIsNone(s['daily'])

    def test_validation(self):
        for value in ['-1', 'NaN', 'inf', '0', '1500']:
            with self.assertRaises(ValueError):
                self.store.save('study', self.study(value))
        self.assertEqual(validate('study', self.study('30,5'))['duration_min'], 30.5)
        data = self.study()
        data['date'] = '2026-02-30'
        with self.assertRaises(ValueError):
            self.store.save('study', data)

    def test_audit_edit_delete(self):
        rid = self.store.save('study', self.study())
        self.store.save('study', self.study(60), rid)
        self.store.delete('study', rid)
        self.assertEqual(self.store.rows('study'), [])
        self.assertEqual([r['action'] for r in self.store.history('study', rid)], ['excluir', 'editar', 'criar'])

    def test_sets_foreign_key_and_delete_guard(self):
        values = {'workout_id': 999, 'exercise': 'Agachamento', 'set_number': 1, 'reps': 10, 'load_basis': 'Total', 'load_kg': 40}
        with self.assertRaises(ValueError):
            self.store.save('sets', values)
        wid = self.workout()
        values['workout_id'] = wid
        sid = self.store.save('sets', values)
        self.assertEqual(len(self.store.rows('sets', '2026-10-16')), 1)
        with self.assertRaises(ValueError):
            self.store.delete('workout', wid)
        self.store.delete('sets', sid)
        self.store.delete('workout', wid)

    def test_overnight_sleep(self):
        values = {'date': '2026-10-16', 'start': '2026-10-15 23:00', 'end': '2026-10-16 07:00', 'awake_min': 30, 'type': 'Sono principal', 'shift': 'Não'}
        self.store.save('sleep', values)
        self.assertEqual(self.store.summary('2026-10-16')['sleep_min'], 450)
        for key, value in [('awake_min', 480), ('end', '2026-10-15 22:00'), ('date', '2026-10-15')]:
            with self.assertRaises(ValueError):
                self.store.save('sleep', values | {key: value})

    def test_medication_dose_and_time(self):
        values = {'date': '2026-10-16', 'name': 'Teste', 'unit': 'mg', 'status': 'Tomado'}
        with self.assertRaises(ValueError):
            self.store.save('medication', values)
        self.store.save('medication', values | {'taken_dose': 10, 'time': '08:00'})
        with self.assertRaises(ValueError):
            self.store.save('medication', values | {'taken_dose': 10, 'status': 'Não tomado'})

    def test_food_unknown_energy(self):
        values = {'date': '2026-10-16', 'meal': 'Almoço', 'food_name': 'Arroz', 'quantity': 100, 'unit': 'g', 'source': 'Não informado'}
        self.store.save('food', values)
        self.store.save('food', values | {'kcal': 130, 'source': 'Estimativa'})
        s = self.store.summary('2026-10-16')
        self.assertEqual(s['kcal'], 130)
        self.assertEqual(s['unknown_kcal'], 1)
        self.assertEqual(s['estimated_foods'], 1)

    def test_unique_daily_and_profile(self):
        values = {'date': '2026-10-16', 'shift': 'Não', 'medicine_status': 'Não informado', 'exercise_status': 'Não informado', 'bible_status': 'Não informado'}
        rid = self.store.save('daily', values)
        with self.assertRaises(ValueError):
            self.store.save('daily', values)
        self.store.save('daily', values | {'shift': 'Sim'}, rid)
        self.store.save('profile', {'name': 'Teste'})
        with self.assertRaises(ValueError):
            self.store.save('profile', {'name': 'Teste 2'})

    def test_backup_restore_and_export(self):
        self.store.save('study', self.study())
        backup = self.store.backup()
        self.store.save('study', self.study(60))
        safety = self.store.restore(backup)
        self.assertNotEqual(backup, safety)
        self.assertTrue(safety.exists())
        self.assertEqual(len(self.store.rows('study')), 1)
        with closing(sqlite3.connect(safety)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM study').fetchone()[0], 2)
        out = Path(self.tmp.name) / 'export.zip'
        self.store.export(out)
        with zipfile.ZipFile(out) as bundle:
            self.assertIn('audit.csv', bundle.namelist())
            self.assertIn('Anatomia', bundle.read('study.csv').decode('utf-8-sig'))

    def test_invalid_restore_preserves_data(self):
        self.store.save('study', self.study())
        bad = Path(self.tmp.name) / 'bad.sqlite3'
        with closing(sqlite3.connect(bad)) as conn:
            conn.execute('PRAGMA user_version=1')
        with self.assertRaises(ValueError):
            self.store.restore(bad)
        self.assertEqual(len(self.store.rows('study')), 1)


if __name__ == '__main__':
    unittest.main()
