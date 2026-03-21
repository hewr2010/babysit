"""测试照片日期解析修复"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_photo_dates():
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
                print("📱 打开应用...")
                page.goto("http://127.0.0.1:5001")
                page.wait_for_load_state('networkidle')
                time.sleep(2)

                print("\n✅ 检查照片日期分组...")

                day_headers = page.locator('.day-header')
                count = day_headers.count()
                print(f"找到{count}个日期分组:")

                dates_found = []
                for i in range(count):
                    date = day_headers.nth(i).locator('.day-date').inner_text()
                    photo_count = day_headers.nth(i).locator('.day-count').inner_text()
                    print(f"  📅 {date} - {photo_count}")
                    dates_found.append(date)

                # 检查是否有3月1日
                has_march_1 = any('03月01日' in d or '3月1日' in d for d in dates_found)
                has_feb_27 = any('02月27日' in d or '2月27日' in d for d in dates_found)
                has_feb_28 = any('02月28日' in d or '2月28日' in d for d in dates_found)

                print("\n验证结果:")
                print(f"  {'✅' if has_march_1 else '❌'} 3月1日的照片")
                print(f"  {'✅' if has_feb_27 else '❌'} 2月27日的照片")
                print(f"  {'✅' if has_feb_28 else '❌'} 2月28日的照片")

                if has_march_1 and has_feb_27 and has_feb_28:
                    print("\n🎉 照片日期解析修复成功！")
                else:
                    print("\n⚠️  部分日期的照片未找到")

                print("\n浏览器保持打开40秒供查看...")
                print("请检查：")
                print("  1. 是否有3月1日的照片")
                print("  2. 是否有2月27、28日的照片")
                print("  3. 各个日期的照片数量是否正确")
                time.sleep(40)

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
