"""Authenticated, three-way synchronization of the shared active-record schema.

No credentials enter SQLite or exports. Device credentials are scoped to one
online account and stored with Windows DPAPI. The transport never follows redirects.
"""
import copy
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from manual_sync import LIMIT, metadata, snapshot, normalized, stamp, preview, apply_file

SITE_URL = 'https://diolino-controle-pessoal.jonathanalencar.chatgpt.site'
STATE_KEY = 'site_sync_state'


class SyncError(Exception):
    pass


class SyncConflict(SyncError):
    def __init__(self, conflicts, base, revision):
        super().__init__('Há alterações nos dois lados. Revise as diferenças antes de sincronizar.')
        self.conflicts, self.base, self.revision = conflicts, base, revision


def validate_connection(data):
    if not isinstance(data, dict) or data.get('format') != 'diolino-site-connection-1' or data.get('url') != SITE_URL:
        raise SyncError('Use uma autorização gerada no site Diolino desta instalação.')
    for key, minimum, maximum in [('device_id', 20, 100), ('device_token', 64, 64), ('gateway_token', 16, 8192), ('account', 1, 200)]:
        value = data.get(key)
        if not isinstance(value, str) or not minimum <= len(value) <= maximum or any(ord(c) < 32 for c in value):
            raise SyncError('Arquivo de autorização inválido.')
    if any(c not in '0123456789abcdef' for c in data['device_token']):
        raise SyncError('Arquivo de autorização inválido.')
    try:
        expiry = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise SyncError('Autorização inválida ou expirada. Gere outra pelo site.') from None
    return {k: data[k] for k in ('format', 'url', 'device_id', 'device_token', 'gateway_token', 'account', 'expires_at')}


class ConnectionVault:
    def __init__(self, directory):
        self.path = Path(directory) / 'site-connection.bin'

    def load(self):
        if not self.path.exists():
            return {}
        from cloud_calendar import PrivateSettings
        return json.loads(PrivateSettings.crypt(self.path.read_bytes(), decrypt=True))

    def save(self, config):
        from cloud_calendar import PrivateSettings
        data = PrivateSettings.crypt(json.dumps(config, ensure_ascii=False).encode())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_bytes(data)
        temporary.replace(self.path)

    def disconnect(self):
        self.path.unlink(missing_ok=True)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SiteClient:
    def __init__(self, config):
        self.config = validate_connection(config)
        # Windows' system trust store is loaded by create_default_context.
        self.opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())

    def request(self, data=None):
        body = None if data is None else json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
        if body and len(body) > LIMIT:
            raise SyncError('A troca excede o limite online de 1,8 MB. Nenhuma alteração foi enviada.')
        headers = {'Authorization': 'Bearer '+self.config['device_token'],
                   'OAI-Sites-Authorization': 'Bearer '+self.config['gateway_token'],
                   'Content-Type': 'application/json', 'Accept': 'application/json',
                   'User-Agent': 'Diolino-Windows-Sync/1.4'}
        request = Request(SITE_URL+'/api/desktop-sync', data=body, headers=headers)
        try:
            with self.opener.open(request, timeout=20) as response:
                if response.headers.get_content_type() != 'application/json':
                    raise SyncError('O site não confirmou a conexão. Gere uma nova autorização.')
                encoded = response.read(LIMIT*3+1)
                if len(encoded) > LIMIT*3:
                    raise SyncError('Resposta acima do limite. Os dados locais foram preservados.')
                result = json.loads(encoded)
                if result.get('device_id') != self.config['device_id']:
                    raise SyncError('A resposta não corresponde a esta conexão.')
                return result
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise SyncError('Conexão expirada, revogada ou não autorizada. Gere outra autorização pelo site.') from None
            if exc.code == 409:
                raise SyncError('Os dados mudaram durante a troca. A próxima tentativa fará nova conferência.') from None
            raise SyncError(f'O site recusou a operação (HTTP {exc.code}). Os dados locais foram preservados.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise SyncError('Sem conexão confirmada com o site. O uso offline continua; haverá nova tentativa.') from None


def export_data(store):
    # Establish device identity without creating temporary plaintext exports.
    meta = metadata(store)
    with store.conn:
        store.conn.execute("INSERT OR REPLACE INTO preferences VALUES('manual_sync',?)", (json.dumps(meta),))
    data = snapshot(store)
    data['records'] = {kind: [row for row in rows if not row.get('deleted_at')] for kind, rows in data['records'].items()}
    return data


def rows_by_id(file, kind):
    return {row['id']: row for row in file.get('records', {}).get(kind, [])}


def record_stamp(file):
    return stamp({key: file.get(key) for key in ('format', 'source', 'records')})


def decisions(plan, destination, incoming, previous_destination, previous_incoming, overrides=None, reverse=False):
    """Only overwrite an unchanged destination, or an explicitly reviewed conflict."""
    choices, unresolved = {}, []
    overrides = overrides or {}
    for conflict in plan['conflicts']:
        kind = conflict['kind']
        source_id = int(conflict['key'].split(':')[1])
        target = conflict['local']
        key = f'{kind}:{source_id if reverse else target["id"]}'
        override = overrides.get(key)
        if override in ('keep', 'incoming'):
            choices[conflict['key']] = ('incoming' if override == 'keep' else 'keep') if reverse else override
            continue
        raw = rows_by_id(incoming, kind)[source_id]
        old_target = rows_by_id(previous_destination, kind).get(target['id'])
        old_source = rows_by_id(previous_incoming, kind).get(source_id)
        if not conflict.get('possible') and old_target and old_source:
            if normalized(kind, target) == normalized(kind, old_target):
                choices[conflict['key']] = 'incoming'
                continue
            if normalized(kind, raw) == normalized(kind, old_source):
                choices[conflict['key']] = 'keep'
                continue
        unresolved.append({**conflict, 'choice_key': key})
    return choices, unresolved


def synchronize(store, client, device_id, overrides=None, expected_base=None, expected_revision=None):
    local = export_data(store)
    saved = store.conn.execute('SELECT value FROM preferences WHERE key=?', (STATE_KEY,)).fetchone()
    baseline = json.loads(saved[0]) if saved else {}
    if baseline.get('device_id') != device_id:
        baseline = {}
    remote = client.request()
    remote_file = remote['file']
    plan = preview(store, remote_file)
    if overrides and (expected_base != plan['base'] or expected_revision != remote['revision']):
        raise SyncError('A prévia mudou. Confira as diferenças novamente antes de aplicar sua escolha.')
    choices, conflicts = decisions(plan, local, remote_file, baseline.get('local', {}), baseline.get('remote', {}), overrides)
    if conflicts:
        raise SyncConflict(conflicts, plan['base'], remote['revision'])
    # Reconcile again with choices to detect actual record or identity changes.
    from manual_sync import reconcile
    candidate = reconcile(snapshot(store), remote_file, choices)['candidate']
    backup = None
    if stamp(candidate) != plan['base']:
        result = apply_file(store, remote_file, plan['base'], choices)
        backup = result['backup']
    merged = export_data(store)
    online_plan = client.request({'action': 'preview', 'file': merged})
    if online_plan['revision'] != remote['revision']:
        raise SyncError('O site mudou durante a troca. Os registros recebidos estão preservados; será feita nova conferência.')
    online_choices, conflicts = decisions(online_plan, remote_file, merged, baseline.get('remote', {}), baseline.get('local', {}), overrides, reverse=True)
    if conflicts:
        # Usually prevented by the local preflight; preserve both versions on races.
        raise SyncError('Há uma diferença online que precisa de nova conferência. Nenhuma versão online foi substituída.')
    if online_plan['counts']['new'] or online_choices or online_plan['counts']['same']:
        # Applying equal rows once also returns aliases to prevent later duplicates.
        # Skip a settled, byte-equivalent exchange on subsequent automatic passes.
        if record_stamp(merged) != record_stamp(baseline.get('local', {})) or record_stamp(remote_file) != record_stamp(baseline.get('remote', {})):
            accepted = client.request({'action': 'apply', 'file': merged, 'revision': online_plan['revision'], 'choices': online_choices})
        else:
            accepted = remote
    else:
        accepted = remote
    state = {'device_id': device_id, 'local': copy.deepcopy(merged), 'remote': accepted['file'], 'at': datetime.now(timezone.utc).isoformat()}
    # Use the snapshot actually sent, even if the UI writes again during HTTP.
    with store.conn:
        store.conn.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)', (STATE_KEY, json.dumps(state, ensure_ascii=False)))
    return {'at': state['at'], 'backup': backup, 'received': plan['counts']['new'],
            'sent': online_plan['counts']['new'], 'blocked': plan['counts']['blocked'],
            'updated': len([v for v in choices.values() if v == 'incoming']) + len([v for v in online_choices.values() if v == 'incoming'])}
