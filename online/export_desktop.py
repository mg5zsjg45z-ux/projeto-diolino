"""Create a local migration file without modifying or uploading desktop records."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import MODELS
from storage import default_directory

parser=argparse.ArgumentParser()
parser.add_argument('--database',type=Path,default=default_directory()/'diolino.sqlite3')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists(): raise SystemExit('Escolha um arquivo novo para preservar a exportação anterior.')
con=sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True)
con.row_factory=sqlite3.Row
try:
    con.execute('BEGIN')
    records={kind:[dict(r) for r in con.execute(f'SELECT * FROM "{kind}" WHERE deleted_at IS NULL ORDER BY id')] for kind in MODELS}
    for row in records['food']:
        nutrition=con.execute('SELECT snapshot_json FROM food_nutrition WHERE food_id=?',(row['id'],)).fetchone()
        if nutrition: row['_nutrition']=json.loads(nutrition[0])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'format':'diolino-desktop-1','records':records},ensure_ascii=False),encoding='utf-8')
    print('Exportação local criada. Nenhum dado foi enviado à internet.')
finally: con.close()
