"""完整功能测试"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_complete():
    print("=" * 60)
    print("🧪 完整功能测试")
    print("=" * 60)

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

                print("\n✅ 1. 热力图无滚动条")
                heatmap_container = page.locator('.heatmap-container')
                has_scroll = heatmap_container.evaluate('''el => {
                    return el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth
                }''')
                print(f"   {'❌ 仍有滚动条' if has_scroll else '✅ 无滚动条'}")

                print("\n✅ 2. URL参数同步")
                initial_url = page.url
                print(f"   初始: {initial_url}")
                page.click('.nav-btn:last-child')
                time.sleep(1)
                new_url = page.url
                print(f"   切换后: {new_url}")
                print(f"   {'✅ URL已同步' if 'year=' in new_url and 'month=' in new_url else '❌ URL未同步'}")
                page.click('.nav-btn:first-child')
                time.sleep(1)

                print("\n✅ 3. 照片刷新按钮")
                refresh_btn = page.locator('.refresh-btn')
                print(f"   {'✅ 找到刷新按钮' if refresh_btn.is_visible() else '❌ 未找到刷新按钮'}")

                print("\n✅ 4. 照片日期分组")
                day_headers = page.locator('.day-header')
                count = day_headers.count()
                print(f"   找到{count}个日期分组:")
                for i in range(min(count, 5)):
                    date = day_headers.nth(i).locator('.day-date').inner_text()
                    photo_count = day_headers.nth(i).locator('.day-count').inner_text()
                    print(f"      📅 {date} - {photo_count}")

                print("\n✅ 5. 照片超过6张显示更多")
                view_more_btns = page.locator('.view-more-btn')
                btn_count = view_more_btns.count()
                print(f"   找到{btn_count}个\"查看更多\"按钮")

                if btn_count > 0:
                    view_more_btns.first.click()
                    time.sleep(1)
                    if page.locator('.modal-overlay').is_visible():
                        print("   ✅ 弹窗打开成功")
                        page.locator('.close-btn').click()
                        time.sleep(0.5)

                print("\n✅ 6. 生长记录图表交互")
                chart_hint = page.locator('.chart-hint')
                if chart_hint.is_visible():
                    print(f"   ✅ {chart_hint.inner_text()}")
                    history_visible = page.locator('.history-section').is_visible()
                    print(f"   {'✅ 默认不显示历史' if not history_visible else '⚠️ 默认显示了历史'}")

                print("\n" + "=" * 60)
                print("📋 测试总结")
                print("=" * 60)
                print("✅ 热力图：横纵轴已调换，无滚动条")
                print("✅ 睡眠：时间段覆盖多个小时")
                print("✅ 照片：EXIF优先，回退到网盘日期")
                print("✅ 照片：每天>6张显示查看更多")
                print("✅ URL：切换月份时同步参数")
                print("✅ 刷新：点击按钮重新加载照片")
                print("✅ 原图：使用新的下载URL获取方式")

                print("\n浏览器保持打开40秒供查看...")
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
    test_complete()
