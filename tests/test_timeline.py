"""测试纵向时光轴相册"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_timeline():
    # 启动服务器
    print("🚀 启动服务器...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "flask", "run", "--port=5001"],
        cwd="/Users/hwr/storage/babysit",
        env={**subprocess.os.environ, "FLASK_APP": "babysit.app"}
    )

    try:
        # 等待服务器启动
        time.sleep(3)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            try:
                print("📱 打开应用...")
                page.goto("http://127.0.0.1:5001")
                page.wait_for_load_state('networkidle')
                time.sleep(2)

                print("\n✅ 检查时光轴相册布局...")

                # 检查是否有timeline结构
                timeline = page.locator('.timeline')
                if timeline.is_visible():
                    print("✅ 找到timeline容器")

                    # 检查日期分组
                    day_headers = page.locator('.day-header')
                    count = day_headers.count()
                    print(f"✅ 找到{count}个日期分组")

                    # 显示每个日期的信息
                    for i in range(min(count, 5)):  # 只显示前5个
                        date = day_headers.nth(i).locator('.day-date').inner_text()
                        photo_count = day_headers.nth(i).locator('.day-count').inner_text()
                        print(f"  📅 {date} - {photo_count}")

                    if count > 5:
                        print(f"  ... 还有{count - 5}个日期")

                    # 检查照片网格
                    photo_grids = page.locator('.photo-grid')
                    total_photos = 0
                    for i in range(photo_grids.count()):
                        photos_in_grid = photo_grids.nth(i).locator('.photo-item').count()
                        total_photos += photos_in_grid

                    print(f"\n✅ 总共{total_photos}张照片")

                else:
                    print("❌ 未找到timeline容器")

                print("\n✅ 测试完成！浏览器保持打开60秒供查看...")
                print("   请滚动查看纵向时光轴效果")
                time.sleep(60)

            except Exception as e:
                print(f"❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10)
            finally:
                browser.close()
    finally:
        print("\n🛑 关闭服务器...")
        server_process.terminate()
        server_process.wait()

if __name__ == '__main__':
    test_timeline()
