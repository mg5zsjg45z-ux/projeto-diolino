"""Development bridge: query the existing SQLite database without modifying it."""
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from storage import Store, SCHEMA_VERSION, default_directory
from dashboard_data import activity_series, habit_calendar, medical_focus_series, recall_series, days_between
from review_cards import review_forecast
from planning import list_plans

def snapshot(path, day, days):
    end = date.fromisoformat(day)
    dates = days_between(end, days)
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        if conn.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
            raise ValueError('Banco incompatível; abra primeiro a versão 2.x.')
        # Reuse read methods without invoking Store's migrating constructor.
        store = Store.__new__(Store)
        store.conn = conn
        store.cache_epoch = 0
        summary = store.summary(day)
        forecast = review_forecast(store,days=7,area='Medicina')
        recall, _ = recall_series(store)
        agenda = [{k:r[k] for k in ('id','date','time','title','duration_min','state')}
                  for d in dates for r in store.rows('agenda',d)]
        agenda.sort(key=lambda r:(r['date'],r['time'] or '99:99',r['id']))
        study_records = [{k:r.get(k) for k in ('id','date','time','topic','duration_min','format','source','learning','notes')}
                         for d in dates for r in store.rows('study',d)]
        study_records.sort(key=lambda r:(r['date'],r['time'] or '99:99',r['id']), reverse=True)
        plans = [{'id':s['id'],'title':s['title'],'plan':p['title'],'state':s['state'],
                  'priority':s['priority'],'due':s['due_date']}
                 for p in list_plans(store,day) if p['status']=='Ativo' for s in p['steps']]
        return {'dates':dates,'series':activity_series(store,end,days),
                'focus':medical_focus_series(store,end,days),'habits':habit_calendar(store,end),
                'forecast':forecast,'recall':recall,'agenda':agenda,'studyRecords':study_records,'tasks':plans,
                'today':{'study':summary['study_min'] if summary['study_count'] else None,
                         'exercise':summary['exercise_min'] if summary['exercise_count'] else None,
                         'sleep':summary['sleep_min']/60 if summary['sleep_count'] else None,
                         'pending':forecast['pending']}}

if __name__ == '__main__':
    if len(sys.argv)!=3:
        raise SystemExit(2)
    try:
        print(json.dumps(snapshot(default_directory()/'diolino.sqlite3',sys.argv[1],int(sys.argv[2])),
                         ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        print(type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
