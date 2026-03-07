#!/usr/bin/env python3
"""测试照片查看器功能"""
import time
from playwright.sync_api import sync_playwright

def test_photo_viewer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("📱 访问应用首页...")
        page.goto('http://localhost:8080', wait_until='networkidle', timeout=15000)
        time.sleep(3)
        
        print("\n📸 查找照片...")
        # 等待照片加载
        photos = page.locator('img[src*="/thumb/"]').all()
        print(f"   找到 {len(photos)} 张照片")
        
        if len(photos) > 0:
            print("\n🖱️  点击第一张照片...")
            photos[0].click()
            time.sleep(2)
            
            # 检查查看器是否打开
            viewer = page.locator('.viewer-overlay')
            if viewer.is_visible():
                print("   ✅ 照片查看器已打开")
                
                # 检查预览图
                preview_img = page.locator('.preview-image, .viewer-content img').first
                if preview_img.is_visible():
                    src = preview_img.get_attribute('src')
                    print(f"   预览图: {src}")
                    
                    # 检查图片是否加载
                    natural_width = preview_img.evaluate("img => img.naturalWidth")
                    natural_height = preview_img.evaluate("img => img.naturalHeight")
                    
                    if natural_width > 0 and natural_height > 0:
                        print(f"   ✅ 预览图加载成功 ({natural_width}x{natural_height})")
                    else:
                        print(f"   ❌ 预览图加载失败")
                
                # 检查时间信息
                photo_info = page.locator('.photo-info').first
                if photo_info.is_visible():
                    info_text = photo_info.text_content()
                    print(f"\n   📅 时间信息:")
                    print(f"   {info_text}")
                    
                    has_date = '📅' in info_text or '20' in info_text
                    has_time = '🕒' in info_text or ':' in info_text
                    
                    if has_date or has_time:
                        print(f"   ✅ 显示时间信息")
                    else:
                        print(f"   ⚠️ 未显示时间信息（可能文件名不含时间）")
                
                # 检查"查看原图"按钮
                download_btn = page.locator('.download-btn, a:has-text("查看原图")').first
                if download_btn.is_visible():
                    href = download_btn.get_attribute('href')
                    print(f"\n   🔗 原图链接:")
                    print(f"   {href[:80]}...")
                    
                    if href:
                        print("   ✅ 原图链接存在")
                        
                        # 测试链接（不实际访问，只检查格式）
                        if 'baidu.com' in href or 'pan.baidu.com' in href:
                            print("   ✅ 链接指向百度网盘")
                        elif href.startswith('http'):
                            print("   ✅ 链接格式正确")
                    else:
                        print("   ❌ 原图链接为空")
                else:
                    print("\n   ⚠️ 未找到'查看原图'按钮")
                
                # 测试左右切换（如果有多张图）
                if len(photos) > 1:
                    print("\n   ⏭️  测试切换到下一张...")
                    next_btn = page.locator('.nav-btn.next').first
                    if next_btn.is_visible():
                        next_btn.click()
                        time.sleep(1)
                        print("   ✅ 可以切换到下一张")
                    else:
                        print("   ⚠️ 未找到下一张按钮")
                
                # 关闭查看器
                print("\n   ❌ 关闭查看器...")
                close_btn = page.locator('.close-btn').first
                close_btn.click()
                time.sleep(1)
                
                if not viewer.is_visible():
                    print("   ✅ 查看器已关闭")
            else:
                print("   ❌ 照片查看器未打开")
        else:
            print("   ⚠️ 没有找到照片（可能还未添加照片）")
        
        # 测试热力图图标
        print("\n📊 检查热力图...")
        heatmap = page.locator('.heatmap-section').first
        if heatmap.is_visible():
            print("   ✅ 热力图可见")
            
            # 检查图例
            legend = page.locator('.legend').first
            if legend.is_visible():
                legend_text = legend.text_content()
                print(f"   图例: {legend_text}")
                
                # 检查emoji图标
                has_bottle = '🍼' in legend_text
                has_sleep = '😴' in legend_text
                has_diaper = '🩲' in legend_text
                has_food = '🥄' in legend_text or '辅食' in legend_text
                
                print(f"   {'✅' if has_bottle else '❌'} 喂奶图标")
                print(f"   {'✅' if has_sleep else '❌'} 睡眠图标")
                print(f"   {'✅' if has_diaper else '❌'} 尿布图标")
                print(f"   {'✅' if not has_food else '❌'} 无辅食（已删除）")
        
        # 测试快捷按钮
        print("\n🎯 检查快捷按钮...")
        quick_actions = page.locator('.quick-actions').first
        if quick_actions.is_visible():
            buttons = page.locator('.action-btn').all()
            print(f"   找到 {len(buttons)} 个按钮")
            
            for btn in buttons:
                label = btn.locator('.action-label').text_content()
                icon = btn.locator('.action-icon').text_content()
                print(f"   {icon} {label}")
            
            has_food_btn = any('辅食' in btn.text_content() for btn in buttons)
            if not has_food_btn:
                print("   ✅ 无辅食按钮（已删除）")
            else:
                print("   ❌ 仍有辅食按钮")
        
        browser.close()
        print("\n✅ 详细测试完成")

if __name__ == '__main__':
    test_photo_viewer()
