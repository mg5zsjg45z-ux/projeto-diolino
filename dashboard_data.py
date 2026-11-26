"""Read-only dashboard data. Unknown observations are never replaced by zero."""
from datetime import date, timedelta, datetime, timezone
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

def recall_series(store, now=None, local_tz=None):
    """Observed medical recall, not model-predicted retention."""
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError('Horário sem fuso.')
    end = now.astimezone(local_tz).date()
    days = days_between(end,7)
    counts = {day:[0,0] for day in days}
    for (raw,) in store.conn.execute(
            "SELECT after_json FROM audit WHERE entity='review_cards' AND action='revisar'"):
        event = json.loads(raw)
        if event.get('area') != 'Medicina' or not event.get('review_log'):
            continue
        log = json.loads(event['review_log'])
        instant = datetime.fromisoformat(log['review_datetime'])
        day = instant.astimezone(local_tz).date().isoformat()
        if day in counts and instant <= now:
            counts[day][0] += int(log['rating'] in (2,3,4))
            counts[day][1] += 1
    return [(day, good/total*100) for day,(good,total) in counts.items() if total], counts
