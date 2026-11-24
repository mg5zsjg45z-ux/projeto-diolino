"""Reproducible UI/query measurements using synthetic data only."""
import cProfile
from datetime import date,timedelta
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import App
from storage import Store
from unified_search import SearchIndex


def run():
    output=Path('test-output/performance-1.3.0');output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        store=Store(folder);today=date.today();stamp=today.isoformat()
        with store.conn:
            store.conn.executemany('INSERT INTO body(date,time,weight_kg,created_at,updated_at) VALUES(?,?,?,?,?)',
                                  [((today-timedelta(days=i//10)).isoformat(),'08:00',80,stamp,stamp) for i in range(3650)])
            store.conn.executemany('INSERT INTO study(date,time,topic,duration_min,format,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                                  [((today-timedelta(days=i//2)).isoformat(),'10:00','Cardiologia de teste',30,'Leitura',stamp,stamp) for i in range(730)])
            store.conn.executemany('INSERT INTO notebook(title,date,body,created_at,updated_at) VALUES(?,?,?,?,?)',
                                  [(f'Nota sintética {i}',stamp,f'Cardiologia e revisão pessoal de teste {i}',stamp,stamp) for i in range(1000)])
        start=time.perf_counter();app=App(store);app.withdraw();app.update_idletasks();construction=(time.perf_counter()-start)*1000
        counts=[0]
        def trace(sql):
            if sql.lstrip().upper().startswith('SELECT'):counts[0]+=1
        store.conn.set_trace_callback(trace)
        pages={}
        try:
            for page in ['home','studies','health_overview','trends','planning','notebook','data']:
                durations=[];queries=[]
                for _ in range(5):
                    counts[0]=0;start=time.perf_counter();app.navigate(page);app.update_idletasks()
                    durations.append((time.perf_counter()-start)*1000);queries.append(counts[0])
                pages[page]=dict(median_ms=round(statistics.median(durations),2),max_ms=round(max(durations),2),selects=statistics.median(queries))
            profile=cProfile.Profile();profile.enable();app.navigate('health_overview');app.update_idletasks();profile.disable()
            profile.dump_stats(output/'health.pstats')
            index=SearchIndex(store)
            try:
                start=time.perf_counter();index.search('cardiologia');cold=(time.perf_counter()-start)*1000
                timings=[]
                for _ in range(10):
                    start=time.perf_counter();index.search('cardilogia');timings.append((time.perf_counter()-start)*1000)
            finally:index.close()
            result=dict(dataset=dict(body=3650,study=730,notes=1000),construction_ms=round(construction,2),
                        pages=pages,search_initial_ms=round(cold,2),search_warm_median_ms=round(statistics.median(timings),2),
                        limits='Synthetic local data; hidden source UI, five repetitions; not real-user or packaged-startup latency.')
            (output/'measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(result))
        finally:app.shutdown()

if __name__=='__main__':run()
