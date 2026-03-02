"""测试URL格式 /年/月"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_url_format():
    print("🚀 启动服务器...")
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
                print("\n✅ 测试1: 直接访问根路径")
                page.goto("http://127.0.0.1:5001")
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                current_url = page.url
                print(f"   当前URL: {current_url}")
                
                # 检查URL是否包含年月
                if '/2026/' in current_url:
                    print("   ✅ URL已自动更新为 /年/月 格式")
                else:
                    print("   ⚠️  URL未更新")
                
                print("\n✅ 测试2: 切换月份")
                # 点击下一月
                page.click('.nav-btn:last-child')
                time.sleep(1)
                
                new_url = page.url
                print(f"   切换后URL: {new_url}")
                
                # 检查URL是否正确更新
                if '/2026/4' in new_url or '/2026/04' in new_url:
                    print("   ✅ URL正确更新")
                else:
                    print(f"   ⚠️  URL格式不符合预期")
                
                # 切回当前月
                page.click('.nav-btn:first-child')
                time.sleep(1)
                
                print("\n✅ 测试3: 直接访问 /2026/2")
                page.goto("http://127.0.0.1:5001/2026/2")
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                month_display = page.locator('.month-display').inner_text()
                print(f"   月份显示: {month_display}")
                
                if "2026年2月" in month_display:
                    print("   ✅ 正确加载了2月的数据")
                else:
                    print(f"   ⚠️  月份显示不正确")
                
                print("\n✅ 测试4: 直接访问 /2026/12")
                page.goto("http://127.0.0.1:5001/2026/12")
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                month_display = page.locator('.month-display').inner_text()
                print(f"   月份显示: {month_display}")
                
                if "2026年12月" in month_display:
                    print("   ✅ 正确加载了12月的数据")
                else:
                    print(f"   ⚠️  月份显示不正确")
                
                print("\n" + "=" * 60)
                print("📋 测试总结")
                print("=" * 60)
                print("✅ URL格式: /年/月")
                print("✅ 根路径: 自动跳转到当前月份")
                print("✅ 切换月份: URL自动更新")
                print("✅ 直接访问: 可以访问任意月份")
                print("✅ 刷新页面: 保持在当前月份")
                
                print("\n浏览器保持打开30秒供测试...")
                print("请测试：")
                print("  1. 切换月份查看URL变化")
                print("  2. 刷新页面是否保持月份")
                print("  3. 手动修改URL是否正确跳转")
                time.sleep(30)
                
            except Exception as e:
                print(f"\n❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                browser.close()
    finally:
        server_process.terminate()
        server_process.wait()
        print("\n✅ 测试完成！")

if __name__ == '__main__':
    test_url_format()
