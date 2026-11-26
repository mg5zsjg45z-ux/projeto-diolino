"""Exercise the 1.4.1 data path using the historical writer and synthetic records."""
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from protected_backup import restore_protected_backup
from storage import Store
from update_backup import encrypted_snapshot


LEGACY_COMMIT = '7f30ea4b7ef8e39a4f456a494039178d46a08d27'
SEED = """
from storage import Store
from review_cards import save_card, rate_card
from theme import VERSION
assert VERSION == '1.4.1'
store = Store('../profile')
store.save('study', dict(topic='Anatomia', date='2026-11-01', duration_min=22, format='Leitura'))
store.save('agenda', dict(date='2026-11-02', title='Revisar', state='Pendente', category='Tarefa', reminder='Não'))
card = save_card(store, 'Pergunta sintética', 'Resposta sintética')
rate_card(store, card['id'], 3, card['revision'])
store.close()
"""


def contents(database):
    tables = ('study', 'agenda', 'preferences', 'audit')
    return {table: [tuple(row) for row in database.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in tables}


class UpgradeTests(unittest.TestCase):
    def test_legacy_records_and_encrypted_recovery(self):
        with tempfile.TemporaryDirectory(dir='test-output') as directory:
            root = Path(directory).resolve()
            legacy = root / 'legacy'
            legacy.mkdir()
            for module in ('storage', 'models', 'energy', 'nutrition', 'review_cards', 'theme'):
                name = module + '.py'
                (legacy / name).write_bytes(subprocess.check_output(['git', 'show', f'{LEGACY_COMMIT}:{name}']))
            subprocess.run([sys.executable, '-X', 'utf8', '-c', SEED], cwd=legacy, check=True)
            source = root / 'profile' / 'diolino.sqlite3'
            with closing(sqlite3.connect(source)) as old:
                before = contents(old)
            backup = root / 'backup.diolinobak'
            password = 'somente teste 2026'
            encrypted_snapshot(source, backup, password)
            with closing(Store(source.parent)) as upgraded:
                self.assertEqual(contents(upgraded.conn), before)
            with closing(Store(root / 'restored')) as restored:
                restore_protected_backup(restored, backup, password)
                self.assertEqual(contents(restored.conn), before)
