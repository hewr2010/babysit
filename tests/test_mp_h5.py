"""
用 Playwright 测试 uni-app H5 编译产物。
H5 与小程序共享同一套 Vue 组件和业务逻辑，
此测试可覆盖数据流、页面渲染、交互等主要路径。
"""
import http.server
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).parent.parent
H5_DIST = ROOT / "frontend-mp" / "dist" / "build" / "h5"


def start_backend():
    proc = subprocess.Popen(
        [sys.executable, "-m", "babysit.app"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # 等待服务启动
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8080/api/baby", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    return proc


def start_static_server():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(H5_DIST), **kwargs)

        def log_message(self, *args, **kwargs):
            pass

    httpd = socketserver.TCPServer(("", 0), Handler)
    httpd.allow_reuse_address = True
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


def test_mp_h5():
    backend = start_backend()
    server, port = start_static_server()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            page.goto(f"http://localhost:{port}/")

            # 认证页
            expect(page.locator("text=宝宝成长日志").first).to_be_visible(timeout=5000)
            input_loc = page.locator("input").first
            expect(input_loc).to_be_visible(timeout=5000)
            input_loc.fill("何与青")
            page.locator(".auth-btn").click()

            # 首页加载
            expect(page.locator(".baby-name")).to_be_visible(timeout=10000)
            page.screenshot(path='/tmp/mp_h5_home.png')
            baby_name = page.locator(".baby-name").text_content()
            assert baby_name, "首页应显示宝宝姓名"
            print(f"宝宝姓名: {baby_name}")

            # 成长记录区域
            expect(page.locator("text=成长记录")).to_be_visible()

            # 相册区域
            page.locator("text=相册").first.click()
            time.sleep(0.5)
            expect(page.locator(".photo-section")).to_be_visible(timeout=5000)

            # 切换到可能有照片的月份（2月），点击左箭头回到过去月份
            for _ in range(4):
                page.locator(".nav-arrow").first.click()
                time.sleep(0.5)
            page.screenshot(path='/tmp/mp_h5_photos.png')

            photos = page.locator(".photo-item").all()
            if photos:
                photos[0].click()
                time.sleep(0.5)
                page.keyboard.press("Escape")
                time.sleep(0.3)
                print(f"照片数量: {len(photos)}")

            # 如果有照片，点击第一张预览
            photos = page.locator(".photo-item").all()
            if photos:
                photos[0].click()
                time.sleep(0.5)
                # uni-app H5 的 previewImage 会打开一个 overlay
                # 按 ESC 或点击空白处关闭
                page.keyboard.press("Escape")
                time.sleep(0.3)

            browser.close()
            print("H5  smoke test passed")
    finally:
        server.shutdown()
        backend.terminate()
        backend.wait()


if __name__ == "__main__":
    test_mp_h5()
