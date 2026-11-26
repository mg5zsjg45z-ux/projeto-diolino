import sqlite3
import unittest
from datetime import date
from dashboard_data import activity_series, habit_calendar, demo_series, days_between

class FakeStore:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute('CREATE TABLE preferences(key TEXT PRIMARY KEY,value TEXT)')
    def summary(self,day):
        return {'study_count':int(day=='2026-11-25'),'study_min':0,
                'exercise_count':0,'exercise_min':0,'sleep_count':0,'sleep_min':0}
    def body_series(self,*args):
        return []

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.addCleanup(self.store.conn.close)
        self.end = date(2026,11,25)
    def test_series_missing_not_zero(self):
        result = activity_series(self.store,self.end,7)
        self.assertEqual(result['study'],[('2026-11-25',0)])
        self.assertEqual(result['exercise'],[])
        self.assertEqual(result['sleep'],[])
    def test_habit_states(self):
        self.store.conn.executemany('INSERT INTO preferences VALUES(?,?)',[
            ('habit_goal:a:2026-11-23','{"name":"Leitura","target":5}'),
            ('habit_day:a:2026-11-23','true'),
            ('habit_day:a:2026-11-24','false')])
        row = habit_calendar(self.store,self.end,7)[0]
        self.assertEqual([status for _,status in row['cells']],
                         ['inactive']*4+['done','missed','unknown'])
    def test_demo_no_store(self):
        self.assertEqual(len(demo_series(self.end,30)['sleep']),30)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM preferences').fetchone()[0],0)
        with self.assertRaises(ValueError):
            days_between(self.end,8)
