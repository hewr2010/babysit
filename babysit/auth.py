import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from flask import jsonify, request

from .config import DATA_DIR

TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
LOGIN_WINDOW_SECONDS = 60
MAX_LOGIN_ATTEMPTS = 10
_failed_logins = {}


def _signing_key():
    configured = os.environ.get('BABYSIT_AUTH_SIGNING_KEY')
    if configured:
        return configured.encode('utf-8')

    key_path = Path(DATA_DIR) / '.auth_signing_key'
    try:
        return key_path.read_bytes()
    except FileNotFoundError:
        pass

    key = secrets.token_bytes(32)
    try:
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as key_file:
            key_file.write(key)
    except FileExistsError:
        return key_path.read_bytes()
    return key


def _signature(expires):
    return hmac.new(_signing_key(), str(expires).encode('ascii'), hashlib.sha256).hexdigest()


def issue_token(password):
    expected = os.environ.get('BABYSIT_ACCESS_PASSWORD', '何与青')
    if not isinstance(password, str) or not hmac.compare_digest(password, expected):
        return None
    expires = int(time.time()) + TOKEN_TTL_SECONDS
    return f'{expires}.{_signature(expires)}'


def token_valid(token):
    if not isinstance(token, str) or token.count('.') != 1:
        return False
    expires, signature = token.split('.')
    if not expires.isdigit() or int(expires) < int(time.time()):
        return False
    return hmac.compare_digest(signature, _signature(int(expires)))


def login_rate_limited(client_id):
    now = time.time()
    recent = [timestamp for timestamp in _failed_logins.get(client_id, []) if now - timestamp < LOGIN_WINDOW_SECONDS]
    recent.append(now)
    _failed_logins[client_id] = recent
    return len(recent) > MAX_LOGIN_ATTEMPTS


def register_auth(app):
    @app.before_request
    def require_access_token():
        if request.path == '/api/auth/login' or request.method == 'OPTIONS':
            return None
        protected_prefixes = ('/api/', '/thumb/', '/preview/', '/video/', '/livp/')
        if not request.path.startswith(protected_prefixes):
            return None
        authorization = request.headers.get('Authorization', '')
        token = authorization[7:] if authorization.startswith('Bearer ') else request.args.get('access_token')
        if not token_valid(token):
            return jsonify({'error': '请先验证访问密码'}), 401
        return None

    @app.post('/api/auth/login')
    def login():
        if login_rate_limited(request.remote_addr or 'unknown'):
            return jsonify({'error': '尝试次数过多，请稍后再试'}), 429
        password = (request.json or {}).get('password', '')
        token = issue_token(password)
        if not token:
            return jsonify({'error': '访问密码不正确'}), 401
        return jsonify({'token': token, 'expires_in': TOKEN_TTL_SECONDS})

    @app.after_request
    def allow_authorized_cross_origin(response):
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
            response.headers['Vary'] = 'Origin'
        return response
