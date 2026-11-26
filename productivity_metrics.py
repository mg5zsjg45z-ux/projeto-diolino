"""Pure productivity rules, independent of UI and persistence."""
from datetime import date

def eisenhower(urgent, important):
    if type(urgent) is not bool or type(important) is not bool:
        raise ValueError('Prioridades devem ser booleanas.')
    return {(True,True): 'fazer', (False,True): 'planejar',
            (True,False): 'delegar', (False,False): 'reavaliar'}[urgent,important]

def adherence(observations):
    """One observation per eligible day; None means unknown."""
    values = list(observations)
    if any(v is not None and type(v) is not bool for v in values):
        raise ValueError('Observação inválida.')
    total = len(values)
    known = sum(v is not None for v in values)
    done = sum(v is True for v in values)
    return dict(eligible=total, evaluated=known, fulfilled=done,
                adherence=done/known if known else None,
                completeness=known/total if total else None,
                lower=done/total if total else None,
                upper=(done+total-known)/total if total else None)

def calendar_observations(start, end, records):
    from datetime import timedelta
    if not isinstance(start,date) or not isinstance(end,date) or end < start:
        raise ValueError('Intervalo inválido.')
    if (end-start).days > 3660:
        raise ValueError('Intervalo excessivo.')
    return [(day.isoformat(), records.get(day.isoformat()))
            for i in range((end-start).days+1)
            for day in [start+timedelta(days=i)]]

def activity_period(store, end, days):
    """Recorded study and exercise minutes, through the selected local date."""
    from datetime import timedelta

    if days not in (7, 30, 90):
        raise ValueError('Selecione 7, 30 ou 90 dias.')
    start = end - timedelta(days=days - 1)
    result = {}
    for kind in ('study', 'workout'):
        row = store.conn.execute(
            f'SELECT SUM(duration_min), COUNT(DISTINCT date) FROM "{kind}" '
            'WHERE deleted_at IS NULL AND date BETWEEN ? AND ?',
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        result[kind] = (row[0], row[1])
    return result
