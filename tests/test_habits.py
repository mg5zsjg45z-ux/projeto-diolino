import tempfile
import unittest

from habits import record_habit, save_habit, week_status
from storage import Store


class HabitTests(unittest.TestCase):
    def test_dated_goals_and_distinct_days(self):
        with tempfile.TemporaryDirectory(dir='test-output') as folder:
            store = Store(folder)
            try:
                key = save_habit(store, 'Ler', 3, '2026-11-23')
                self.assertEqual(week_status(store, '2026-11-22'), [])
                self.assertIsNone(week_status(store, '2026-11-23')[0]['today'])
                for value in (False, True, True):
                    record_habit(store, key, '2026-11-23', value)
                save_habit(store, 'Ler', 4, '2026-11-24', key)
                self.assertEqual(week_status(store, '2026-11-23')[0]['target'], 3)
                row = week_status(store, '2026-11-24')[0]
                self.assertEqual((row['done'], row['observed'], row['target']), (1, 1, 4))
                self.assertEqual(week_status(store, '2026-11-30')[0]['done'], 0)
            finally:
                store.close()
