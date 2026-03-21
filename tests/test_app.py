#!/usr/bin/env python3
"""使用playwright测试babysit应用"""
import time
from playwright.sync_api import sync_playwright

def test_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("📱 访问应用首页...")
        page.goto('http://localhost:8080', wait_until='networkidle', timeout=10000)

        # 等待页面加载
        time.sleep(2)

        print("\n🔍 检查页面标题...")
        title = page.title()
        print(f"   标题: {title}")

        # 检查疫苗提醒区域
        print("\n💉 检查疫苗提醒...")
        vaccine_section = page.locator('.vaccine-section').first
        if vaccine_section.is_visible():
            print("   ✅ 疫苗区域可见")

            # 获取所有疫苗链接
            vaccine_links = page.locator('.vaccine-item').all()
            print(f"   找到 {len(vaccine_links)} 个疫苗提醒")

            for i, link in enumerate(vaccine_links[:3]):  # 只检查前3个
                href = link.get_attribute('href')
                text = link.text_content()
                print(f"   [{i+1}] {text[:30]}... -> {href}")

                # 测试链接是否可访问
                if href:
                    try:
                        response = page.request.get(href, timeout=5000)
                        status = response.status
                        print(f"       状态码: {status} {'✅' if status == 200 else '❌'}")
                    except Exception as e:
                        print(f"       ❌ 访问失败: {str(e)[:50]}")
        else:
            print("   ❌ 疫苗区域不可见")

        # 检查照片区域
        print("\n📸 检查照片区域...")
        photo_section = page.locator('.photo-section').first
        if photo_section.is_visible():
            print("   ✅ 照片区域可见")

            # 等待照片加载
            time.sleep(2)

            # 查找缩略图
            thumbnails = page.locator('img[src*="/thumb/"]').all()
            print(f"   找到 {len(thumbnails)} 张缩略图")

            if thumbnails:
                # 检查第一张图片
                first_thumb = thumbnails[0]
                src = first_thumb.get_attribute('src')
                print(f"   第一张图片 src: {src}")

                # 检查图片是否加载成功
                natural_width = first_thumb.evaluate("img => img.naturalWidth")
                natural_height = first_thumb.evaluate("img => img.naturalHeight")

                if natural_width > 0 and natural_height > 0:
                    print(f"   ✅ 图片加载成功 ({natural_width}x{natural_height})")
                else:
                    print(f"   ❌ 图片加载失败")

                    # 检查网络请求
                    print("\n   检查图片请求...")
                    with page.expect_response(lambda r: '/thumb/' in r.url) as response_info:
                        page.reload()
                    response = response_info.value
                    print(f"   图片请求状态: {response.status}")
                    print(f"   图片URL: {response.url}")
        else:
            print("   ⚠️ 照片区域不可见（可能没有照片）")

        # 检查控制台错误
        print("\n🐛 检查控制台错误...")
        console_messages = []
        page.on('console', lambda msg: console_messages.append(msg))
        page.reload()
        time.sleep(2)

        errors = [msg for msg in console_messages if msg.type in ['error', 'warning']]
        if errors:
            print(f"   ⚠️ 发现 {len(errors)} 个错误/警告:")
            for msg in errors[:5]:  # 只显示前5个
                print(f"     - [{msg.type}] {msg.text[:100]}")
        else:
            print("   ✅ 无控制台错误")

        # 截图
        print("\n📷 保存截图...")
        page.screenshot(path='/tmp/babysit_screenshot.png', full_page=True)
        print("   保存到: /tmp/babysit_screenshot.png")

        browser.close()
        print("\n✅ 测试完成")

if __name__ == '__main__':
    test_app()
