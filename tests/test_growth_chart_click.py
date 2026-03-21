"""测试生长记录点击图表显示详情功能"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_growth_chart_click():
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

                # 查找生长记录section
                growth_section = page.locator('section.growth-section')

                # 检查是否有记录
                if page.locator('.empty-state').is_visible():
                    print("⚠️  没有记录，请先手动添加一些生长记录")
                    print("   浏览器保持打开60秒供添加数据...")
                    time.sleep(60)
                    return

                print("✅ 已有生长记录")

                # 检查是否显示提示文字
                hint = page.locator('.chart-hint')
                if hint.is_visible():
                    print(f"✅ 提示文字显示: {hint.inner_text()}")
                else:
                    print("❌ 提示文字未显示")

                # 检查默认是否没有记录详情
                history_visible = page.locator('.history-section').is_visible()
                if not history_visible:
                    print("✅ 默认不显示记录详情")
                else:
                    print("⚠️  默认显示了记录详情（应该不显示）")

                print("\n🖱️  测试点击图表...")
                print("   请手动点击图表上的数据点")
                print("   观察是否出现记录详情和删除按钮")
                print("   浏览器保持打开60秒...")
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
    test_growth_chart_click()
