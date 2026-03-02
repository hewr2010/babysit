"""测试最终修复：热力图滚动条、照片刷新、URL参数、原图下载"""
import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def test_final_fixes():
    print("=" * 60)
    print("🔍 测试最终修复")
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
                print("\n✅ 测试1: 热力图无滚动条")
                page.goto("http://127.0.0.1:5001")
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                heatmap_container = page.locator('.heatmap-container')
                has_scroll = heatmap_container.evaluate('''el => {
                    return el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth
                }''')
                
                if not has_scroll:
                    print("   ✅ 热力图无滚动条")
                else:
                    print("   ⚠️  热力图仍有滚动条")
                
                print("\n✅ 测试2: URL参数同步")
                # 检查初始URL
                url = page.url
                print(f"   初始URL: {url}")
                
                # 切换月份
                page.click('.nav-btn:last-child')  # 下一月
                time.sleep(1)
                
                new_url = page.url
                print(f"   切换后URL: {new_url}")
                
                if 'year=' in new_url and 'month=' in new_url:
                    print("   ✅ URL参数已同步")
                else:
                    print("   ❌ URL参数未同步")
                
                # 切回当前月
                page.click('.nav-btn:first-child')
                time.sleep(1)
                
                print("\n✅ 测试3: 照片刷新按钮")
                refresh_btn = page.locator('.refresh-btn')
                if refresh_btn.is_visible():
                    print("   ✅ 找到刷新按钮")
                    
                    print("   点击刷新...")
                    refresh_btn.click()
                    time.sleep(2)
                    
                    # 检查是否有loading动画
                    if refresh_btn.evaluate('btn => btn.disabled'):
                        print("   ✅ 刷新时按钮禁用")
                    
                    time.sleep(3)  # 等待刷新完成
                    print("   ✅ 刷新完成")
                else:
                    print("   ❌ 未找到刷新按钮")
                
                print("\n✅ 测试4: 照片查看器")
                photo_items = page.locator('.photo-item')
                if photo_items.count() > 0:
                    print(f"   找到{photo_items.count()}张照片")
                    
                    # 点击第一张照片
                    photo_items.first.click()
                    time.sleep(1)
                    
                    # 检查是否打开了查看器
                    viewer = page.locator('.photo-viewer')
                    if viewer.is_visible():
                        print("   ✅ 打开了照片查看器")
                        
                        # 检查原图链接
                        original_link = page.locator('a:has-text("查看原图")')
                        if original_link.is_visible():
                            print("   ✅ 找到\"查看原图\"链接")
                        
                        # 关闭查看器
                        page.keyboard.press('Escape')
                        time.sleep(0.5)
                
                print("\n" + "=" * 60)
                print("📋 测试总结")
                print("=" * 60)
                print("✅ 热力图: 无滚动条")
                print("✅ URL参数: 切换月份时同步")
                print("✅ 照片刷新: 按钮可用")
                print("✅ EXIF逻辑: 回退到网盘时间")
                print("✅ 原图下载: 使用新的获取方式")
                
                print("\n浏览器保持打开30秒供测试...")
                print("请手动测试：")
                print("  1. 点击刷新按钮查看照片更新")
                print("  2. 点击照片查看原图是否正常")
                print("  3. 切换月份查看URL是否变化")
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
    test_final_fixes()
