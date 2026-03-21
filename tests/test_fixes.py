#!/usr/bin/env python3
"""测试所有修复"""
import time
from playwright.sync_api import sync_playwright

def test_fixes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("📱 访问应用...")
        page.goto('http://localhost:8080', wait_until='networkidle', timeout=15000)
        time.sleep(3)

        # 1. 测试疫苗链接
        print("\n💉 测试疫苗链接...")
        vaccines = page.locator('.vaccine-item').all()
        if vaccines:
            first_vaccine = vaccines[0]
            href = first_vaccine.get_attribute('href')
            text = first_vaccine.text_content()
            print(f"   第一个疫苗: {text[:30]}")
            print(f"   链接: {href}")

            # 测试链接
            try:
                response = page.request.get(href, timeout=10000)
                print(f"   状态: {response.status} {'✅' if response.status == 200 else '❌'}")

                if 'dxy.com' in href:
                    print(f"   ✅ 使用丁香医生链接")
                else:
                    print(f"   ⚠️ 不是丁香医生链接")
            except Exception as e:
                print(f"   ❌ 访问失败: {str(e)[:50]}")

        # 2. 测试照片时间显示
        print("\n📸 测试照片时间显示...")
        photos = page.locator('img[src*="/thumb/"]').all()
        if photos:
            print(f"   找到 {len(photos)} 张照片")

            # 点击第一张
            photos[0].click()
            time.sleep(2)

            viewer = page.locator('.viewer-overlay')
            if viewer.is_visible():
                photo_info = page.locator('.photo-info').first
                info_text = photo_info.text_content()
                print(f"   时间信息: {info_text}")

                # 检查是否显示了非3月2日的日期
                if '📅' in info_text:
                    print(f"   ✅ 显示日期图标")
                if '🕒' in info_text or ':' in info_text:
                    print(f"   ✅ 显示时间信息")

                # 关闭查看器
                close_btn = page.locator('.close-btn').first
                close_btn.click()
                time.sleep(1)

        # 3. 测试生长记录
        print("\n📏 测试生长记录...")
        growth_section = page.locator('.growth-section').first
        if growth_section.is_visible():
            print("   ✅ 生长区域可见")

            # 检查最新数据卡片
            growth_cards = page.locator('.growth-card').all()
            if growth_cards:
                for card in growth_cards:
                    label = card.locator('.growth-label').text_content()
                    value = card.locator('.growth-value').text_content()
                    unit = card.locator('.growth-unit').text_content()
                    print(f"   {label}: {value} {unit}")

                    # 检查体重单位
                    if '体重' in label:
                        if 'g' in unit:
                            print(f"   ✅ 体重单位为g")
                        else:
                            print(f"   ❌ 体重单位不是g: {unit}")

            # 检查历史记录列表
            history_items = page.locator('.history-item').all()
            if history_items:
                print(f"   找到 {len(history_items)} 条历史记录")

                # 检查删除按钮
                delete_btns = page.locator('.delete-btn').all()
                print(f"   找到 {len(delete_btns)} 个删除按钮")
                if delete_btns:
                    print(f"   ✅ 删除功能已添加")

            # 点击添加按钮测试预填充
            add_btn = page.locator('.add-btn').first
            add_btn.click()
            time.sleep(1)

            modal = page.locator('.modal-sheet')
            if modal.is_visible():
                print("\n   测试生长记录模态框...")

                # 检查体重单位
                weight_label = page.locator('label:has-text("体重")').first
                label_text = weight_label.text_content()
                print(f"   体重标签: {label_text}")

                if '(g)' in label_text:
                    print(f"   ✅ 输入框体重单位为g")
                else:
                    print(f"   ❌ 输入框体重单位不是g")

                # 检查是否有预填充值
                height_input = page.locator('input[type="number"]').nth(0)
                height_value = height_input.input_value()

                if height_value:
                    print(f"   ✅ 身高预填充: {height_value}")
                else:
                    print(f"   ℹ️ 身高未预填充（可能没有历史记录）")

                # 关闭模态框
                close_btn = page.locator('.close-btn').first
                close_btn.click()
                time.sleep(1)

        browser.close()
        print("\n✅ 测试完成")

if __name__ == '__main__':
    test_fixes()
