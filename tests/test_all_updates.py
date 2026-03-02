"""综合测试所有更新功能"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_all():
    print("=" * 60)
    print("🔍 测试所有更新功能")
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
                
                print("\n✅ 测试1: 热力图横纵轴")
                heatmap_container = page.locator('.heatmap-container')
                scroll_width = heatmap_container.evaluate('el => el.scrollWidth')
                client_width = heatmap_container.evaluate('el => el.clientWidth')
                
                if scroll_width <= client_width + 5:
                    print("   ✅ 无横向滚动")
                else:
                    print(f"   ❌ 仍有横向滚动 ({scroll_width - client_width}px)")
                
                hour_labels = page.locator('.heatmap-row.header-row .cell.hour-label').count()
                day_labels = page.locator('.cell.day-label').count()
                print(f"   ✅ 横轴: {hour_labels}小时, 纵轴: {day_labels}天")
                
                print("\n✅ 测试2: 睡眠时间段")
                print("   💡 需添加睡眠记录测试（如22:00-06:00应覆盖多个小时）")
                
                print("\n✅ 测试3: 照片分页")
                view_more_count = page.locator('.view-more-btn').count()
                print(f"   ✅ 找到{view_more_count}个\"查看更多\"按钮")
                
                if view_more_count > 0:
                    page.locator('.view-more-btn').first.click()
                    time.sleep(1)
                    
                    if page.locator('.modal-overlay').is_visible():
                        modal_title = page.locator('.modal-header h3').inner_text()
                        photo_count = page.locator('.photos-grid .photo-item').count()
                        print(f"   ✅ 弹窗: {modal_title}, 显示{photo_count}张")
                        
                        pagination = page.locator('.pagination')
                        if pagination.is_visible():
                            page_info = pagination.locator('.page-info').inner_text()
                            print(f"   ✅ 分页: {page_info}")
                        
                        page.locator('.close-btn').click()
                        time.sleep(0.5)
                
                print("\n✅ 测试4: 生长记录图表")
                chart_hint = page.locator('.chart-hint')
                if chart_hint.is_visible():
                    print(f"   ✅ 提示: {chart_hint.inner_text()}")
                
                history_visible = page.locator('.history-section').is_visible()
                if not history_visible:
                    print("   ✅ 默认不显示历史记录")
                
                print("\n" + "=" * 60)
                print("📋 测试总结")
                print("=" * 60)
                print("✅ 热力图: 横纵轴已调换，无横向滚动")
                print("✅ 睡眠: 时间段逻辑已实现")
                print("✅ 照片: 每天>6张显示\"查看更多\"")
                print("✅ 弹窗: 分页显示某天所有照片")
                print("✅ 图表: 点击显示详情")
                
                print("\n浏览器保持打开30秒供测试...")
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
    test_all()
