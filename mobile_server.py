"""Authenticated, LAN-only browser companion using the desktop SQLite database."""
import argparse
from dataclasses import asdict
from datetime import date
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import tempfile
import threading
import time
from urllib.parse import urlparse, parse_qs

from storage import Store, default_directory
from models import MODELS, CHECK_GROUPS
from project_sync import write_snapshot
from cloud_calendar import SERIES_PREFIX
from energy import energy_estimate
from theme import VERSION
from planning import list_plans, upcoming_steps, create_plan, check_step, duplicate_plan, TEMPLATES


def lan_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.connect(('192.168.0.1', 80))
        address = connection.getsockname()[0]
    if not ipaddress.ip_address(address).is_private:
        raise ValueError('Conecte este computador a uma rede local para abrir o Diolino no iPhone.')
    return address


class MobileServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()
    def __init__(self, address, directory, code):
        self.directory, self.code = Path(directory), code
        self.sessions, self.failures, self.jobs = {}, {}, {}
        self.lock = threading.RLock()
        self.ai_lock = threading.Lock()
        with_store = Store(directory)
        with_store.daily_backup()
        with_store.close()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'Diolino'
    def log_message(self, *args):
        pass  # No personal request bodies, cookies or query strings in logs.

    def reply(self, status, value, content_type='application/json; charset=utf-8', cookie=None):
        data = json.dumps(value, ensure_ascii=False).encode() if content_type.startswith('application/json') else value
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; connect-src 'self'")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        host = self.headers.get('Host', '')
        port = self.server.server_port
        allowed = {f'{self.server.server_address[0]}:{port}', f'127.0.0.1:{port}', f'localhost:{port}'}
        return host in allowed

    def session(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookie['diolino'].value
        except (KeyError, ValueError):
            return None
        with self.server.lock:
            record = self.server.sessions.get(token)
            if not record or record['expires'] < time.monotonic():
                self.server.sessions.pop(token, None)
                return None
            return token, record

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Endereço não autorizado.'})
        path = urlparse(self.path)
        if path.path == '/':
            return self.reply(200, (Path(__file__).parent / 'mobile/index.html').read_bytes(), 'text/html; charset=utf-8')
        if path.path in ('/mobile/modern.css', '/mobile/planning.js'):
            mime = 'text/css' if path.path.endswith('.css') else 'text/javascript'
            return self.reply(200, (Path(__file__).parent / path.path.lstrip('/')).read_bytes(), mime + '; charset=utf-8')
        if path.path == '/health':
            return self.reply(200, {'status': 'ok', 'application': 'Diolino mobile', 'version': VERSION})
        session = self.session()
        if not session:
            return self.reply(401, {'error': 'Entre com o código exibido neste computador.'})
        if path.path == '/api/session':
            return self.reply(200, {'csrf': session[1]['csrf']})
        if path.path == '/api/schema':
            return self.reply(200, {k: {'label': label, 'fields': [asdict(f) for f in fields]} for k, (label, fields) in MODELS.items()})
        store = None
        try:
            with self.server.lock:
                store = Store(self.server.directory)
                query = parse_qs(path.query)
                day = query.get('day', [date.today().isoformat()])[0]
                date.fromisoformat(day)
                if path.path == '/api/overview':
                    result = {'summary': store.summary(day), 'pillars': store.pillar_states(day), 'checks': store.checklist(day),
                              'check_groups': CHECK_GROUPS, 'upcoming': store.upcoming_agenda(day)[:20],
                              'weight_series': store.body_series('weight_kg', '1900-01-01', day)[-90:],
                              'planned_steps': upcoming_steps(store, day)[:10]}
                elif path.path == '/api/plans':
                    result = {'plans': list_plans(store, day), 'templates': TEMPLATES}
                elif path.path == '/api/records':
                    kind = query.get('kind', [''])[0]
                    if kind not in MODELS:
                        raise ValueError('Tipo inválido.')
                    result = store.rows(kind, day if query.get('filter') == ['day'] and kind != 'profile' and kind != 'sets' else None)
                    if kind == 'agenda':
                        for row in result:
                            row['_readonly'] = bool(store.conn.execute('SELECT 1 FROM calendar_links WHERE agenda_id=? AND uid LIKE ?', (row['id'], SERIES_PREFIX + '%')).fetchone())
                    result = result[:2000]
                elif path.path == '/api/taco':
                    from nutrition import catalogue
                    result = catalogue().search(query.get('q', [''])[0])[:50]
                else:
                    return self.reply(404, {'error': 'Página não encontrada.'})
            self.reply(200, result)
        except (ValueError, KeyError) as exc:
            self.reply(400, {'error': str(exc)})
        finally:
            if store:
                store.close()

    def do_POST(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Endereço não autorizado.'})
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.reply(403, {'error': 'Origem não autorizada.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 25 * 1024 * 1024:
                return self.reply(413, {'error': 'Envie até 25 MB por vez.'})
            if self.path == '/api/login':
                data = json.loads(self.rfile.read(min(length, 10000)))
                with self.server.lock:
                    now = time.monotonic()
                    count, until = self.server.failures.get(self.client_address[0], (0, 0))
                    if until > now:
                        return self.reply(429, {'error': 'Aguarde um minuto antes de tentar novamente.'})
                    supplied = str(data.get('code', '')).replace('-', '').replace(' ', '')
                    if not secrets.compare_digest(supplied, self.server.code):
                        count += 1
                        self.server.failures[self.client_address[0]] = (count, now + 60 if count >= 5 else 0)
                        return self.reply(401, {'error': 'Código incorreto.'})
                    self.server.failures.pop(self.client_address[0], None)
                    token, csrf = secrets.token_hex(32), secrets.token_hex(24)
                    self.server.sessions[token] = {'csrf': csrf, 'expires': now + 43200}
                return self.reply(200, {'csrf': csrf}, cookie=f'diolino={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200')
            session = self.session()
            if not session:
                return self.reply(401, {'error': 'Entre novamente para continuar.'})
            if not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), session[1]['csrf']):
                return self.reply(403, {'error': 'Recarregue a página antes de salvar.'})
            data = json.loads(self.rfile.read(length))
            with self.server.lock:
                store = Store(self.server.directory)
                try:
                    if self.path == '/api/logout':
                        self.server.sessions.pop(session[0], None)
                        return self.reply(200, {'ok': True}, cookie='diolino=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                    if self.path == '/api/plans/create':
                        result = {'id': create_plan(store, data['values'], data.get('steps', []))}
                    elif self.path == '/api/plans/check':
                        check_step(store, data['id'], data['checked'])
                        result = {'ok': True}
                    elif self.path == '/api/plans/duplicate':
                        result = {'id': duplicate_plan(store, data['id'])}
                    elif self.path == '/api/check':
                        day, key = data['day'], data['key']
                        date.fromisoformat(day)
                        checked = data['checked']
                        if not isinstance(checked, bool):
                            raise ValueError('Checagem inválida.')
                        if key.endswith('_status'):
                            store.set_pillar(day, key, checked)
                        else:
                            store.set_check(day, key, checked)
                        result = {'ok': True}
                    elif self.path in ('/api/save', '/api/delete'):
                        kind = data['kind']
                        if kind not in MODELS:
                            raise ValueError('Tipo inválido.')
                        rid = data.get('id')
                        if rid is not None and (type(rid) is not int or not store.get(kind, rid)):
                            raise ValueError('Registro não encontrado.')
                        if kind == 'agenda' and rid and store.conn.execute('SELECT 1 FROM calendar_links WHERE agenda_id=? AND uid LIKE ?', (rid, SERIES_PREFIX + '%')).fetchone():
                            raise ValueError('Edite esta ocorrência no Calendário da Apple.')
                        if self.path == '/api/delete':
                            if rid is None:
                                raise ValueError('Selecione um registro.')
                            store.delete(kind, rid)
                            result = {'ok': True}
                        else:
                            nutrition = None
                            if kind == 'food' and data.get('taco_code'):
                                from nutrition import catalogue
                                nutrition = catalogue().snapshot(str(data['taco_code']))
                            elif kind == 'food' and rid and data['values'].get('source') == 'TACO (NEPA/UNICAMP)':
                                nutrition = store.get('food', rid).get('_nutrition')
                            result = {'id': store.save(kind, data['values'], rid, nutrition=nutrition)}
                    elif self.path == '/api/energy':
                        return self.reply(200, energy_estimate(**data))
                    else:
                        return self.reply(404, {'error': 'Ação não encontrada.'})
                    write_snapshot(store)
                    self.reply(200, result)
                finally:
                    store.close()
        except (ValueError, KeyError, TypeError) as exc:
            self.reply(400, {'error': str(exc)[:300]})
        except Exception:
            self.reply(500, {'error': 'Não foi possível concluir. Os registros já salvos foram preservados.'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=default_directory())
    parser.add_argument('--host', default=None)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    config_path = args.data_dir / 'mobile-access.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {'code': ''.join(str(secrets.randbelow(10)) for _ in range(12))}
    host = args.host or lan_address()
    if not ipaddress.ip_address(host).is_private or host == '0.0.0.0':
        raise ValueError('Use um endereço da rede local.')
    try:
        server = MobileServer((host, args.port), args.data_dir, config['code'])
    except OSError:
        return
    config.update(url=f'http://{host}:{args.port}', port=args.port, pid=os.getpid())
    config_path.write_text(json.dumps(config), encoding='utf-8')
    server.serve_forever(poll_interval=0.5)


if __name__ == '__main__':
    main()
