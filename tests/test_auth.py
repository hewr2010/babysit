import time

from babysit.app import create_app
from babysit.auth import _signature


def test_authentication_protects_api_and_media(monkeypatch):
    monkeypatch.setenv('BABYSIT_AUTH_SIGNING_KEY', 'unit-test-signing-key-with-32-bytes')
    monkeypatch.setenv('BABYSIT_ACCESS_PASSWORD', 'a-strong-family-password')
    client = create_app().test_client()

    assert client.get('/api/baby').status_code == 401
    assert client.get('/thumb/example.jpg').status_code == 401
    assert client.get('/preview/example.jpg').status_code == 401
    assert client.get('/video/example.mp4').status_code == 401
    assert client.post('/api/auth/login', json={'password': 'wrong'}).status_code == 401

    response = client.post('/api/auth/login', json={'password': 'a-strong-family-password'})
    assert response.status_code == 200
    token = response.get_json()['token']
    assert token.count('.') == 1

    assert client.get('/api/baby', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    assert client.get(f'/thumb/example.jpg?access_token={token}').status_code == 200
    assert client.get(f'/preview/example.jpg?access_token={token}').status_code == 200
    assert client.get('/api/baby', headers={'Authorization': 'Bearer invalid.token'}).status_code == 401

    expired = int(time.time()) - 1
    expired_token = f'{expired}.{_signature(expired)}'
    assert client.get('/api/baby', headers={'Authorization': f'Bearer {expired_token}'}).status_code == 401
