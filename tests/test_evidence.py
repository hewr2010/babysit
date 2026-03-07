"""证据收集测试 - 证明 bug 已修复"""
import subprocess
import time
import sys
import os
sys.path.insert(0, '/Users/hwr/storage/babysit')

from playwright.sync_api import sync_playwright

# 清理特定测试文件的缓存
test_files = [
    'babysit/data/cache/thumbs/2026-03-07%20120000_200x200.jpg',
    'babysit/data/cache/thumbs/2026-03-07%20120000_800x800.jpg',
]
for f in test_files:
    if os.path.exists(f):
        os.remove(f)
        print(f"[清理] {f}")

# 启动服务器
print("[启动服务器...]")
server = subprocess.Popen(
    [sys.executable, "-c", 
     "from babysit.app import create_app; app = create_app(); app.run(host='127.0.0.1', port=8089, debug=False, threaded=True)"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=1,
    universal_newlines=True,
)

time.sleep(3)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        
        print("[访问页面...]")
        page.goto('http://127.0.0.1:8089/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        
        # 截图1: 初始状态
        page.screenshot(path='/Users/hwr/storage/babysit/evidence_1_initial.png', full_page=True)
        print("[截图1] 已保存: evidence_1_initial.png")
        
        # 等待5秒让后端处理
        print("[等待后端处理...]")
        page.wait_for_timeout(5000)
        
        # 截图2: 5秒后状态
        page.screenshot(path='/Users/hwr/storage/babysit/evidence_2_after_5s.png', full_page=True)
        print("[截图2] 已保存: evidence_2_after_5s.png")
        
        # 再等5秒
        page.wait_for_timeout(5000)
        
        # 截图3: 10秒后状态
        page.screenshot(path='/Users/hwr/storage/babysit/evidence_3_after_10s.png', full_page=True)
        print("[截图3] 已保存: evidence_3_after_10s.png")
        
        browser.close()
        
    print("\n[收集后端日志...]")
    # 获取服务器输出
    import select
    
    stdout_data = []
    stderr_data = []
    
    # 非阻塞读取输出
    import fcntl
    
    def set_non_blocking(fd):
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    if server.stdout:
        set_non_blocking(server.stdout.fileno())
        try:
            while True:
                line = server.stdout.readline()
                if not line:
                    break
                stdout_data.append(line.strip())
        except:
            pass
    
    if server.stderr:
        set_non_blocking(server.stderr.fileno())
        try:
            while True:
                line = server.stderr.readline()
                if not line:
                    break
                stderr_data.append(line.strip())
        except:
            pass
    
    print("\n[后端日志输出]")
    print("-" * 60)
    for line in stdout_data[-30:]:
        print(f"stdout: {line}")
    for line in stderr_data[-30:]:
        print(f"stderr: {line}")
    print("-" * 60)
    
    print("\n[证据收集完成]")
    
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except:
        server.kill()
