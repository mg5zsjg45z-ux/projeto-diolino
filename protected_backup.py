"""Authenticated password-protected SQLite exports. Passwords are never persisted."""
import os
import sqlite3
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.exceptions import InvalidTag

MAGIC = b'DIOLINO-BACKUP\x01'
MAX_SIZE = 256*1024*1024


def key_for(password,salt):
    if not isinstance(password,str) or not password:
        raise ValueError('Informe a senha do backup.')
    return Argon2id(salt=salt,length=32,iterations=3,lanes=4,memory_cost=65536).derive(password.encode('utf-8'))


def create_protected_backup(store,path,password):
    return encrypt_payload(serialize_backup(store),path,password)


def serialize_backup(store):
    memory=sqlite3.connect(':memory:')
    try:
        store.conn.backup(memory)
        return memory.serialize()
    finally:
        memory.close()


def encrypt_payload(payload,path,password):
    if len(password)<12:
        raise ValueError('Use uma senha com pelo menos 12 caracteres.')
    if len(payload)>MAX_SIZE:
        raise ValueError('O banco excede o limite de 256 MiB deste exportador.')
    salt,nonce=os.urandom(16),os.urandom(12)
    encrypted=AESGCM(key_for(password,salt)).encrypt(nonce,payload,MAGIC+salt)
    # Exclusive creation preserves an earlier backup even if a filename is reused.
    with Path(path).open('xb') as file:
        file.write(MAGIC+salt+nonce+encrypted)
    return Path(path)


def decrypt_backup(path,password):
    path=Path(path)
    if path.stat().st_size>MAX_SIZE+1024:
        raise ValueError('Backup acima do limite de 256 MiB.')
    data=path.read_bytes();offset=len(MAGIC)
    if not data.startswith(MAGIC) or len(data)<offset+16+12+16:
        raise ValueError('Arquivo de backup protegido inválido.')
    salt,nonce=data[offset:offset+16],data[offset+16:offset+28]
    try:
        payload=AESGCM(key_for(password,salt)).decrypt(nonce,data[offset+28:],MAGIC+salt)
    except InvalidTag:
        raise ValueError('Senha incorreta ou arquivo alterado. Nenhum dado foi restaurado.') from None
    if not payload.startswith(b'SQLite format 3\x00'):
        raise ValueError('O arquivo não contém um banco SQLite.')
    return payload


def restore_protected_backup(store,path,password):
    return restore_payload(store,decrypt_backup(path,password))


def restore_payload(store,payload):
    # Store.restore validates schema/integrity and creates a backup before replacing data.
    with tempfile.TemporaryDirectory(prefix='restore-',dir=store.directory) as directory:
        temporary=Path(directory)/'incoming.sqlite3'
        temporary.write_bytes(payload)
        return store.restore(temporary)
