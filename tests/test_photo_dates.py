"""测试照片日期提取"""
import time
import subprocess
import sys

def test_photo_dates():
    print("🚀 启动服务器重新扫描照片...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "flask", "run", "--port=5001"],
        cwd="/Users/hwr/storage/babysit",
        env={**subprocess.os.environ, "FLASK_APP": "babysit.app"}
    )
    
    try:
        time.sleep(3)
        
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            try:
                print("📱 打开应用...")
                page.goto("http://127.0.0.1:5001")
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                print("\n等待照片加载（这会触发EXIF提取）...")
                print("浏览器会开始下载和生成缩略图...")
                
                # 等待一段时间让缩略图生成
                time.sleep(30)
                
                print("\n✅ 检查照片日期...")
                
                # 检查有多少个日期分组
                day_headers = page.locator('.day-header')
                count = day_headers.count()
                print(f"找到{count}个日期分组")
                
                if count > 0:
                    for i in range(min(count, 10)):
                        date = day_headers.nth(i).locator('.day-date').inner_text()
                        photo_count = day_headers.nth(i).locator('.day-count').inner_text()
                        print(f"  📅 {date} - {photo_count}")
                
                print("\n浏览器保持打开60秒...")
                print("请检查：")
                print("  1. 照片是否按正确的日期分组")
                print("  2. 3月是否有多个日期（而不是全部在3月2日）")
                print("  3. 点击刷新按钮重新加载")
                time.sleep(60)
                
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
    test_photo_dates()
