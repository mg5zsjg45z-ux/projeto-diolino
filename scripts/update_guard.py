"""Offline pre-update snapshot. Does not migrate or replace the live database."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

def snapshot(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or source == destination:
        raise ValueError('Invalid source or destination')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise ValueError('Invalid snapshot')
                if dst.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Invalid foreign keys')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(snapshot(args.source, args.destination))
