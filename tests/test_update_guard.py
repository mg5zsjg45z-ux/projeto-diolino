import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from scripts.update_guard import snapshot

class UpdateGuardTests(unittest.TestCase):
    def test_snapshot_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'source.sqlite3'
            target = Path(folder)/'backup.sqlite3'
            with closing(sqlite3.connect(source)) as db:
                db.execute('create table sample (value text)')
                db.execute("insert into sample values ('preserved')")
                db.commit()
                snapshot(source,target)
                with closing(sqlite3.connect(target)) as copy:
                    self.assertEqual(copy.execute('select value from sample').fetchone(), ('preserved',))
                with self.assertRaises(FileExistsError):
                    snapshot(source,target)
                with self.assertRaises(ValueError):
                    snapshot(source,source)
                self.assertEqual(db.execute('select value from sample').fetchone(), ('preserved',))
