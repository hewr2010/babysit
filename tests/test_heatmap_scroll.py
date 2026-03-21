"""快速测试热力图横向滚动"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_heatmap():
    server_process = subprocess.Popen(
        [sys.executable, "-m", "flask", "run", "--port=5001"],
        cwd="/Users/hwr/storage/babysit",
        env={**subprocess.os.environ, "FLASK_APP": "babysit.app"}
    )

    try:
        time.sleep(3)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            try:
                page.goto("http://127.0.0.1:5001")
                page.wait_for_load_state('networkidle')
                time.sleep(2)

                heatmap_container = page.locator('.heatmap-container')
                scroll_width = heatmap_container.evaluate('el => el.scrollWidth')
                client_width = heatmap_container.evaluate('el => el.clientWidth')

                print(f"scrollWidth: {scroll_width}")
                print(f"clientWidth: {client_width}")

                if scroll_width <= client_width + 5:
                    print("✅ 无横向滚动")
                else:
                    print(f"⚠️ 仍有横向滚动 (差值: {scroll_width - client_width}px)")

                time.sleep(30)
            finally:
                browser.close()
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == '__main__':
    test_heatmap()
