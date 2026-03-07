"""浏览器端到端测试 - 验证功能完整性"""
import subprocess
import time
import sys
sys.path.insert(0, '/Users/hwr/storage/babysit')

from playwright.sync_api import sync_playwright, expect


def test_app():
    """测试应用功能"""
    # 启动服务器
    server = subprocess.Popen(
        [sys.executable, "-c", 
         "from babysit.app import create_app; app = create_app(); app.run(host='127.0.0.1', port=8088, debug=False, threaded=True)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    try:
        # 等待服务器启动
        time.sleep(3)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            
            # 1. 测试首页加载
            print("[Test] 加载首页...")
            page.goto('http://127.0.0.1:8088/', wait_until='domcontentloaded')
            page.wait_for_timeout(3000)  # 等待 Vue 渲染
            
            # 截图 - 首页
            page.screenshot(path='/Users/hwr/storage/babysit/test_screenshot_home.png', full_page=True)
            print("[Test] 首页截图已保存: test_screenshot_home.png")
            
            # 2. 验证页面标题
            title = page.title()
            print(f"[Test] 页面标题: {title}")
            assert '青青' in title or '成长' in title, f"标题异常: {title}"
            
            # 3. 验证没有喂奶/大便/小便按钮
            print("[Test] 检查按钮...")
            page.wait_for_timeout(1000)
            
            feeding_btn = page.locator('text=喂奶')
            poop_btn = page.locator('text=大便')
            pee_btn = page.locator('text=小便')
            
            assert feeding_btn.count() == 0, "不应该有喂奶按钮"
            assert poop_btn.count() == 0, "不应该有大便按钮"
            assert pee_btn.count() == 0, "不应该有小便按钮"
            print("[Test] ✅ 喂奶/大便/小便按钮已删除")
            
            # 4. 验证身高/体重按钮存在
            height_btn = page.locator('text=身高')
            weight_btn = page.locator('text=体重')
            
            assert height_btn.count() > 0, "应该有身高按钮"
            assert weight_btn.count() > 0, "应该有体重按钮"
            print("[Test] ✅ 身高/体重按钮存在")
            
            # 5. 验证没有热力图
            heatmap = page.locator('.heatmap-section')
            assert heatmap.count() == 0, "不应该有热力图"
            print("[Test] ✅ 热力图已删除")
            
            # 6. 验证生长记录区域存在
            growth_section = page.locator('.growth-section')
            if growth_section.count() == 0:
                growth_section = page.locator('text=生长记录')
            assert growth_section.count() > 0, "应该有生长记录区域"
            print("[Test] ✅ 生长记录区域存在")
            
            # 7. 验证相册区域存在
            photo_section = page.locator('.photo-section')
            if photo_section.count() == 0:
                photo_section = page.locator('text=相册')
            assert photo_section.count() > 0, "应该有相册区域"
            print("[Test] ✅ 相册区域存在")
            
            # 8. 点击身高按钮测试弹窗
            print("[Test] 测试身高弹窗...")
            height_btn.first.click()
            page.wait_for_timeout(500)
            
            # 截图 - 弹窗
            page.screenshot(path='/Users/hwr/storage/babysit/test_screenshot_modal.png')
            print("[Test] 弹窗截图已保存: test_screenshot_modal.png")
            
            # 关闭弹窗
            page.keyboard.press('Escape')
            page.wait_for_timeout(300)
            
            # 9. 验证 API 响应
            print("[Test] 验证 API...")
            
            # 测试 /api/baby
            response = page.evaluate("() => fetch('/api/baby').then(r => r.json())")
            assert 'name' in response, f"API /api/baby 返回异常: {response}"
            print(f"[Test] ✅ /api/baby 正常: {response.get('name')}")
            
            # 测试 /api/growth
            response = page.evaluate("() => fetch('/api/growth').then(r => r.json())")
            assert isinstance(response, list), f"API /api/growth 返回异常: {response}"
            print(f"[Test] ✅ /api/growth 正常: {len(response)} 条记录")
            
            # 测试已删除的 API 返回 404
            response = page.evaluate("() => fetch('/api/records/2025/1').then(r => r.status)")
            assert response == 404, f"API /api/records 应该返回 404，实际: {response}"
            print("[Test] ✅ /api/records 已删除 (404)")
            
            browser.close()
            
        print("\n" + "="*50)
        print("✅ 所有测试通过!")
        print("="*50)
        
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    test_app()
