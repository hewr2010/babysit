"""测试新功能：热力图横纵轴调换、睡眠时间段、照片分页"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_new_features():
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

                # ===== 测试1: 热力图横纵轴 =====
                print("\n" + "=" * 60)
                print("✅ 测试1: 热力图横纵轴")
                print("=" * 60)

                heatmap = page.locator('.heatmap')
                if heatmap.is_visible():
                    print("✅ 找到热力图")

                    # 检查第一行（表头）的小时标签
                    header_row = page.locator('.heatmap-row.header-row')
                    hour_labels = header_row.locator('.cell.hour-label')
                    count = hour_labels.count()
                    print(f"✅ 横轴有{count}个时间点（应该是24）")

                    # 检查纵轴的日期标签
                    day_labels = page.locator('.cell.day-label')
                    day_count = day_labels.count()
                    print(f"✅ 纵轴有{day_count}个日期")

                    # 检查是否有横向滚动条
                    heatmap_container = page.locator('.heatmap-container')
                    scroll_width = heatmap_container.evaluate('el => el.scrollWidth')
                    client_width = heatmap_container.evaluate('el => el.clientWidth')

                    if scroll_width <= client_width + 10:  # 允许一点误差
                        print("✅ 无横向滚动条")
                    else:
                        print(f"⚠️  仍有横向滚动 (scrollWidth: {scroll_width}, clientWidth: {client_width})")
                else:
                    print("❌ 未找到热力图")

                # ===== 测试2: 照片"查看更多"按钮 =====
                print("\n" + "=" * 60)
                print("✅ 测试2: 照片分页")
                print("=" * 60)

                view_more_btns = page.locator('.view-more-btn')
                btn_count = view_more_btns.count()

                if btn_count > 0:
                    print(f"✅ 找到{btn_count}个\"查看更多\"按钮")

                    # 点击第一个按钮
                    print("\n点击第一个\"查看更多\"按钮...")
                    view_more_btns.first.click()
                    time.sleep(1)

                    # 检查是否打开了弹窗
                    day_modal = page.locator('.modal-overlay')
                    if day_modal.is_visible():
                        print("✅ 打开了DayPhotosModal弹窗")

                        # 检查标题
                        modal_title = page.locator('.modal-header h3').inner_text()
                        print(f"   标题: {modal_title}")

                        # 检查是否有照片网格
                        photos_grid = page.locator('.photos-grid')
                        if photos_grid.is_visible():
                            photo_items = photos_grid.locator('.photo-item').count()
                            print(f"✅ 弹窗中显示{photo_items}张照片")

                        # 检查是否有分页
                        pagination = page.locator('.pagination')
                        if pagination.is_visible():
                            page_info = pagination.locator('.page-info').inner_text()
                            print(f"✅ 分页信息: {page_info}")

                        # 关闭弹窗
                        page.locator('.close-btn').click()
                        time.sleep(0.5)
                        print("✅ 关闭弹窗")
                    else:
                        print("❌ 未打开弹窗")
                else:
                    print("⚠️  本月没有超过6张照片的日期")

                # ===== 测试3: 睡眠时间段（需要手动检查） =====
                print("\n" + "=" * 60)
                print("✅ 测试3: 睡眠时间段")
                print("=" * 60)
                print("💡 需要手动测试：")
                print("   1. 添加一条睡眠记录（设置开始和结束时间）")
                print("   2. 观察热力图中睡眠图标是否覆盖多个小时")
                print("   3. 例如：22:00-06:00 应该在22,23,0,1,2,3,4,5,6点都显示😴")

                print("\n✅ 浏览器保持打开60秒供测试...")
                print("   请检查：")
                print("   - 热力图横轴是24小时，纵轴是日期")
                print("   - 照片超过6张的日期有\"查看更多\"按钮")
                print("   - 点击\"查看更多\"打开分页弹窗")
                time.sleep(60)

            except Exception as e:
                print(f"\n❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10)
            finally:
                browser.close()
    finally:
        print("\n🛑 关闭服务器...")
        server_process.terminate()
        server_process.wait()
        print("\n✅ 测试完成！")

if __name__ == '__main__':
    test_new_features()
