import os
import subprocess
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

BASE_URL = 'http://127.0.0.1:8099'


def wait_for_backend():
    for _ in range(50):
        try:
            urllib.request.urlopen(f'{BASE_URL}/', timeout=1)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError('Backend did not start')


def test_h5_authentication():
    env = {
        **os.environ,
        'PORT': '8099',
        'DEBUG': '0',
        'BABYSIT_ACCESS_PASSWORD': 'test-strong-password',
        'BABYSIT_AUTH_SIGNING_KEY': 'integration-test-signing-key',
    }
    process = subprocess.Popen(
        ['/Users/hwr/storage/babysit/.venv/bin/python', '-m', 'babysit.app'],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_backend()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            )
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            assert page.request.get(f'{BASE_URL}/api/baby').status == 401
            page.goto(BASE_URL)
            expect(page.locator('.auth-wall')).to_be_visible(timeout=15000)
            page.locator('.auth-input').fill('wrong-password')
            page.locator('.auth-btn').click()
            expect(page.locator('.auth-error')).to_contain_text('不正确')
            page.locator('.auth-input').fill('test-strong-password')
            page.locator('.auth-btn').click()
            expect(page.locator('.baby-name').first).to_be_visible(timeout=15000)
            token = page.evaluate("JSON.parse(localStorage.getItem('baby_auth_verified')).token")
            assert token.count('.') == 1
            for image in page.locator('img').all():
                src = image.get_attribute('src') or ''
                if '/thumb/' in src or '/preview/' in src:
                    assert 'access_token=' in src
            fresh_page = browser.new_page()
            assert fresh_page.request.get(f'{BASE_URL}/api/baby').status == 401
            fresh_page.goto(f'{BASE_URL}/2026/11')
            expect(fresh_page.locator('.auth-wall')).to_be_visible(timeout=10000)
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == '__main__':
    test_h5_authentication()
