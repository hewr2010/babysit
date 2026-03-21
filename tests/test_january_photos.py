#!/usr/bin/env python3
"""测试1月份照片显示EXIF时间"""
import time
from playwright.sync_api import sync_playwright

def test_january_photos():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("📱 访问应用...")
        page.goto('http://localhost:8080', wait_until='networkidle', timeout=15000)
        time.sleep(3)

        print("\n📅 切换到2026年1月...")
        # 点击月份选择器的后退按钮两次（3月 -> 2月 -> 1月）
        prev_btn = page.locator('.nav-btn').first
        prev_btn.click()
        time.sleep(2)
        prev_btn.click()
        time.sleep(3)

        # 检查月份标题
        month_title = page.locator('.section-title:has-text("照片")').first
        title_text = month_title.text_content()
        print(f"当前月份: {title_text}")

        print("\n📸 检查照片...")
        photos = page.locator('img[src*="/thumb/"]').all()
        print(f"找到 {len(photos)} 张照片")

        if photos:
            # 点击第一张（应该是DSC照片）
            print("\n点击第一张照片...")
            photos[0].click()
            time.sleep(2)

            viewer = page.locator('.viewer-overlay')
            if viewer.is_visible():
                photo_info = page.locator('.photo-info').first
                info_text = photo_info.text_content()
                print(f"\n照片信息:")
                print(f"{info_text}")

                # 检查日期
                if '2026-01-05' in info_text:
                    print("\n✅ 显示正确的EXIF拍摄日期 (2026-01-05)")
                elif '📅' in info_text and '2026' in info_text:
                    date = [line for line in info_text.split('\n') if '📅' in line]
                    print(f"\n✅ 显示日期: {date}")
                else:
                    print("\n⚠️ 未找到日期信息")

                # 检查时间
                if '16:20' in info_text or '🕒' in info_text:
                    print("✅ 显示拍摄时间")

        browser.close()
        print("\n✅ 测试完成")

if __name__ == '__main__':
    test_january_photos()
