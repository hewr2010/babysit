"""简单URL格式测试"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

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
        
        print("测试1: 访问根路径")
        page.goto("http://127.0.0.1:5001")
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        print(f"URL: {page.url}")
        
        print("\n测试2: 切换月份")
        page.click('.nav-btn:last-child')
        time.sleep(1)
        print(f"URL: {page.url}")
        
        print("\n测试3: 访问 /2026/2")
        page.goto("http://127.0.0.1:5001/2026/2")
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        month_display = page.locator('.month-display').inner_text()
        print(f"月份: {month_display}")
        print(f"URL: {page.url}")
        
        print("\n测试完成，浏览器保持打开30秒...")
        time.sleep(30)
        
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
