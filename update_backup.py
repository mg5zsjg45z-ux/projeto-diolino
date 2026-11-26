"""Encrypted snapshot taken from a read-only SQLite connection before an update."""
import argparse
from contextlib import closing
from getpass import getpass
from pathlib import Path
import sqlite3

from protected_backup import decrypt_backup, encrypt_payload


def encrypted_snapshot(source, destination, password):
    source = Path(source).resolve(strict=True)
    destination = Path(destination)
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as database:
        with closing(sqlite3.connect(':memory:')) as copy:
            database.backup(copy)
            if copy.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Banco inconsistente.')
            if copy.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('Referência inválida no banco.')
            payload = copy.serialize()
    destination.parent.mkdir(parents=True, exist_ok=True)
    encrypt_payload(payload, destination, password)
    if decrypt_backup(destination, password) != payload:
        raise ValueError('A verificação do backup falhou.')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    secret = getpass('Senha do backup pré-atualização (mínimo 12 caracteres): ')
    if secret != getpass('Confirme a senha: '):
        parser.error('As senhas diferem.')
    print(encrypted_snapshot(args.source, args.destination, secret))
