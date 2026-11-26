import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from fsrs import Card
from review_cards import review_forecast

class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TABLE preferences (key TEXT PRIMARY KEY, value TEXT)')
        self.store = SimpleNamespace(conn=self.conn)
        self.now = datetime(2026, 11, 25, 22, tzinfo=timezone.utc)

    def add(self, key, due, area='Medicina', archived=False):
        card = Card()
        card.due = due
        row = dict(id=key, area=area, archived=archived, schedule=card.to_json())
        self.conn.execute('INSERT INTO preferences VALUES (?, ?)',
                          ('review_card:'+key, json.dumps(row)))

    def test_boundaries_filter_and_read_only(self):
        self.add('a', self.now)
        self.add('b', self.now+timedelta(hours=1))
        self.add('c', self.now+timedelta(hours=6))
        self.add('d', self.now+timedelta(days=7))
        self.add('e', self.now, archived=True)
        self.add('f', self.now, area='Bíblia')
        before = self.conn.execute('SELECT * FROM preferences').fetchall()
        result = review_forecast(self.store, now=self.now, area='Medicina',
                                 local_tz=timezone(timedelta(hours=-3)))
        self.assertEqual(result['pending'], 1)
        self.assertEqual([d['count'] for d in result['days']], [1,1,0,0,0,0,0])
        self.assertEqual(result['days'][0]['date'], '2026-11-25')
        self.assertEqual(before, self.conn.execute('SELECT * FROM preferences').fetchall())

    def test_empty_and_invalid(self):
        self.assertEqual(review_forecast(self.store, now=self.now)['pending'], 0)
        for days in (0, 91, True, 1.5):
            with self.assertRaises(ValueError):
                review_forecast(self.store, days=days, now=self.now)
        with self.assertRaises(ValueError):
            review_forecast(self.store, now=self.now.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            review_forecast(self.store, now=self.now, area='invalid')
