"""Read-only dashboard data. Unknown observations are never replaced by zero."""
from datetime import date, timedelta
import json

PERIODS = (7, 30, 90)

def days_between(end, count):
    if type(end) is not date or type(count) is not int or count not in PERIODS:
        raise ValueError('Período inválido.')
    return [(end - timedelta(days=count-1-i)).isoformat() for i in range(count)]

def activity_series(store, end, count):
    result = {'study': [], 'exercise': [], 'sleep': []}
    for day in days_between(end, count):
        row = store.summary(day)
        for name, key, total, divisor in (
            ('study','study_count','study_min',1),
            ('exercise','exercise_count','exercise_min',1),
            ('sleep','sleep_count','sleep_min',60)):
            if row[key]:
                result[name].append((day,row[total]/divisor))
    result['weight'] = store.body_series('weight_kg', days_between(end,count)[0], end.isoformat())
    return result

def habit_calendar(store, end, count=30):
    days = days_between(end, count)
    goals = {}
    for key, raw in store.conn.execute("SELECT key,value FROM preferences WHERE key GLOB 'habit_goal:*' ORDER BY key"):
        _, habit, effective = key.split(':')
        if effective <= days[-1]:
            value = json.loads(raw)
            if habit not in goals:
                goals[habit] = {'id':habit,'first':effective,'name':value['name']}
            goals[habit]['name'] = value['name']
    observations = {}
    for key, raw in store.conn.execute("SELECT key,value FROM preferences WHERE key GLOB 'habit_day:*'"):
        _, habit, day = key.split(':')
        value = json.loads(raw)
        if type(value) is bool and days[0] <= day <= days[-1]:
            observations[habit,day] = value
    for habit, row in goals.items():
        row['cells'] = [(day, 'inactive' if day < row['first'] else
                        {True:'done',False:'missed',None:'unknown'}[observations.get((habit,day))])
                        for day in days]
    return sorted(goals.values(),key=lambda row:row['name'].casefold())

def demo_series(end,count):
    """Synthetic chart values only; never writes into a Store."""
    days = days_between(end,count)
    return {'study':[(day,35+(i*17)%55) for i,day in enumerate(days) if i%6!=0],
            'exercise':[(day,20+(i*11)%40) for i,day in enumerate(days) if i%4!=0],
            'sleep':[(day,6+(i*3)%5/2) for i,day in enumerate(days)],
            'weight':[(day,80-i*.025) for i,day in enumerate(days) if i%5==0]}
