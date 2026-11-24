"""Planner periods and views over existing agenda and plan-step records."""
import calendar
from datetime import date,timedelta


def period(day,mode):
    selected=date.fromisoformat(day)
    if mode=='day':start,count=selected,1
    elif mode=='week':start,count=selected-timedelta(days=selected.weekday()),7
    elif mode=='month':start,count=selected.replace(day=1),calendar.monthrange(selected.year,selected.month)[1]
    else:raise ValueError('Período inválido.')
    return [(start+timedelta(days=i)).isoformat() for i in range(count)]


def shift(day,mode,amount):
    selected=date.fromisoformat(day)
    if mode=='month':
        year,month=divmod(selected.year*12+selected.month-1+amount,12);month+=1
        return selected.replace(year=year,month=month,day=min(selected.day,calendar.monthrange(year,month)[1])).isoformat()
    if mode not in ('day','week'):raise ValueError('Período inválido.')
    return (selected+timedelta(days=amount*(7 if mode=='week' else 1))).isoformat()


def planner_data(store,day,mode):
    dates=period(day,mode);start,end=dates[0],dates[-1]
    events=[r for r in store.rows('agenda') if start<=r['date']<=end and r['state']!='Cancelado']
    plans={r['id']:r for r in store.rows('plans') if r['status']=='Ativo'}
    steps=[dict(r,plan_title=plans[r['plan_id']]['title']) for r in store.rows('plan_steps')
           if r['plan_id'] in plans and r['due_date'] and start<=r['due_date']<=end]
    undated=[dict(r,plan_title=plans[r['plan_id']]['title']) for r in store.rows('plan_steps')
             if r['plan_id'] in plans and not r['due_date'] and r['state']!='Concluído']
    return dict(dates=dates,events=sorted(events,key=lambda r:(r['date'],r['time'] or '',r['id'])),steps=steps,undated=undated)


def hours(events,full=False):
    result=set(range(24) if full else range(6,23))
    result.update(int(row['time'][:2]) for row in events if row['time'])
    return sorted(result)
