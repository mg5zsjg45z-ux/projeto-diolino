import unittest
from datetime import date
from productivity_metrics import eisenhower, adherence, calendar_observations

class MetricsTests(unittest.TestCase):
    def test_quadrants(self):
        self.assertEqual(eisenhower(True,True),'fazer')
        self.assertEqual(eisenhower(False,True),'planejar')
        self.assertEqual(eisenhower(True,False),'delegar')
        self.assertEqual(eisenhower(False,False),'reavaliar')
        with self.assertRaises(ValueError):
            eisenhower(1,False)

    def test_missing(self):
        result = adherence([True,False,None,None])
        self.assertEqual(result['adherence'],.5)
        self.assertEqual(result['completeness'],.5)
        self.assertEqual(result['lower'],.25)
        self.assertEqual(result['upper'],.75)
        self.assertIsNone(adherence([])['adherence'])
        self.assertIsNone(adherence([None])['adherence'])

    def test_calendar(self):
        self.assertEqual(calendar_observations(date(2026,1,1),date(2026,1,2),
                         {'2026-01-01':False}), [('2026-01-01',False),('2026-01-02',None)])

    def test_period_counts_distinct_days_and_preserves_missing(self):
        from tempfile import TemporaryDirectory
        from storage import Store
        from productivity_metrics import activity_period
        with TemporaryDirectory(dir='test-output') as directory:
            store = Store(directory)
            try:
                for day in ('2026-10-31', '2026-11-01', '2026-11-01', '2026-11-07', '2026-11-08'):
                    store.save('study', dict(date=day, topic='Revisão', duration_min=20, format='Leitura'))
                result = activity_period(store, date(2026, 11, 7), 7)
                self.assertEqual(result, {'study': (60, 2), 'workout': (None, 0)})
            finally:
                store.close()
