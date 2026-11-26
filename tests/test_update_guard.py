import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from scripts.update_guard import snapshot

class UpdateGuardTests(unittest.TestCase):
    def test_encrypted_snapshot_restores_record(self):
        from protected_backup import decrypt_backup
        from update_backup import encrypted_snapshot
        with tempfile.TemporaryDirectory(dir='test-output') as folder:
            source = Path(folder) / 'original.sqlite3'
            target = Path(folder) / 'copy.diolinobak'
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE example (n INTEGER)')
                db.execute('INSERT INTO example VALUES (42)')
                db.commit()
            encrypted_snapshot(source, target, 'somente teste 123')
            with closing(sqlite3.connect(':memory:')) as restored:
                restored.deserialize(decrypt_backup(target, 'somente teste 123'))
                self.assertEqual(restored.execute('SELECT n FROM example').fetchone(), (42,))

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
