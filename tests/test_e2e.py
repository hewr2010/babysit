#!/usr/bin/env python3
"""
Playwright E2E 测试
测试所有功能是否正常工作
"""
import subprocess
import time
import sys
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:8080"

def wait_for_server():
    """等待服务器启动"""
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(BASE_URL, timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False

def test_baby_info(page):
    """测试宝宝信息显示"""
    print("🧪 测试宝宝信息...")
    page.goto(BASE_URL)
    page.wait_for_selector(".baby-name", timeout=10000)

    # 验证宝宝名称和年龄显示
    baby_name = page.locator(".baby-name").text_content()
    baby_age = page.locator(".baby-age").text_content()

    assert baby_name, "宝宝名称应该显示"
    assert baby_age, "宝宝年龄应该显示"
    print(f"   ✅ 宝宝信息: {baby_name}, {baby_age}")

def test_month_selector(page):
    """测试月份切换"""
    print("🧪 测试月份切换...")
    page.goto(BASE_URL)
    page.wait_for_selector(".month-display", timeout=10000)

    # 获取当前月份
    current_month = page.locator(".month-display").text_content()

    # 点击下个月
    page.locator(".month-selector .nav-btn").nth(1).click()
    page.wait_for_timeout(500)

    new_month = page.locator(".month-display").text_content()
    assert new_month != current_month, "月份应该切换"
    print(f"   ✅ 月份切换: {current_month} -> {new_month}")

def test_summary_cards(page):
    """测试昨日总结卡片"""
    print("🧪 测试昨日总结...")
    page.goto(BASE_URL)
    page.wait_for_selector(".summary-card", timeout=10000)

    cards = page.locator(".summary-card").count()
    assert cards == 3, f"应该有3个总结卡片，实际有{cards}个"

    # 验证卡片内容
    labels = ["睡眠时长", "喂奶次数", "换尿布"]
    for i, label in enumerate(labels):
        card_label = page.locator(".summary-card .card-label").nth(i).text_content()
        assert card_label == label, f"第{i+1}个卡片应该是{label}"

    print(f"   ✅ 昨日总结显示正常")

def test_heatmap(page):
    """测试热力图显示和交互"""
    print("🧪 测试热力图...")
    page.goto(BASE_URL)
    page.wait_for_selector(".heatmap", timeout=10000)

    # 验证热力图存在
    heatmap = page.locator(".heatmap")
    expect(heatmap).to_be_visible()

    # 验证时间段标签
    hour_labels = page.locator(".hour-label").count()
    assert hour_labels == 8, f"应该有8个时间段，实际有{hour_labels}个"

    print(f"   ✅ 热力图显示正常")

def test_growth_section(page):
    """测试生长记录区域"""
    print("🧪 测试生长记录...")
    page.goto(BASE_URL)
    page.wait_for_selector(".growth-section", timeout=10000)

    # 验证生长记录区域存在
    growth = page.locator(".growth-section")
    expect(growth).to_be_visible()

    # 检查是否有生长数据卡片或空状态
    cards = page.locator(".growth-card").count()
    empty = page.locator(".growth-section .empty-state").count()

    assert cards > 0 or empty > 0, "应该显示生长数据或空状态"

    if cards > 0:
        # 验证曲线图存在
        chart = page.locator(".chart-container")
        expect(chart).to_be_visible()
        print(f"   ✅ 生长记录显示正常，有{cards}个数据卡片和曲线图")
    else:
        print(f"   ✅ 生长记录显示空状态")

def test_vaccine_section(page):
    """测试疫苗提醒区域"""
    print("🧪 测试疫苗提醒...")
    page.goto(BASE_URL)
    page.wait_for_selector(".vaccine-section", timeout=10000)

    # 验证疫苗区域存在
    vaccine = page.locator(".vaccine-section")
    expect(vaccine).to_be_visible()

    # 检查疫苗列表或空状态
    items = page.locator(".vaccine-item").count()
    print(f"   ✅ 疫苗提醒显示正常，有{items}个疫苗项目")

def test_photo_section(page):
    """测试照片区域"""
    print("🧪 测试照片区域...")
    page.goto(BASE_URL)
    page.wait_for_selector(".photo-section", timeout=10000)

    # 验证照片区域存在
    photo_section = page.locator(".photo-section")
    expect(photo_section).to_be_visible()

    # 检查照片或空状态
    photos = page.locator(".photo-item").count()
    empty = page.locator(".photo-section .empty-state").count()

    assert photos > 0 or empty > 0, "应该显示照片或空状态"

    if photos > 0:
        print(f"   ✅ 照片区域显示正常，有{photos}张照片")

        # 检查是否有时间标签
        time_labels = page.locator(".photo-time").count()
        print(f"   📸 其中{time_labels}张照片显示拍摄时间")
    else:
        print(f"   ✅ 照片区域显示空状态")

def test_quick_actions(page):
    """测试底部快捷操作"""
    print("🧪 测试快捷操作...")
    page.goto(BASE_URL)
    page.wait_for_selector(".quick-actions", timeout=10000)

    # 验证快捷操作栏存在
    actions = page.locator(".quick-actions")
    expect(actions).to_be_visible()

    # 验证有5个操作按钮（喂奶、睡眠、尿布、辅食、生长）
    buttons = page.locator(".action-btn").count()
    assert buttons == 5, f"应该有5个快捷按钮，实际有{buttons}个"

    # 测试点击喂奶按钮弹出记录弹窗
    page.locator(".action-btn.feeding").click()
    page.wait_for_selector(".modal-sheet", timeout=5000)

    modal_title = page.locator(".modal-title").text_content()
    assert "喂奶" in modal_title, "应该显示喂奶记录弹窗"

    # 关闭弹窗
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    print(f"   ✅ 快捷操作正常，弹窗可正常打开")

def test_responsive_layout(page):
    """测试响应式布局"""
    print("🧪 测试响应式布局...")

    # 测试手机端
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(BASE_URL)
    page.wait_for_selector(".app-container", timeout=10000)

    # 手机端应该全宽
    container = page.locator(".app-container")
    box = container.bounding_box()
    assert box["width"] <= 375, f"手机端宽度应该是375px，实际是{box['width']}px"
    print(f"   ✅ 手机端布局正常 (宽度: {box['width']}px)")

    # 测试PC端
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(BASE_URL)
    page.wait_for_selector(".app-container", timeout=10000)

    container = page.locator(".app-container")
    box = container.bounding_box()
    # PC端应该居中且有限宽度
    assert box["width"] <= 680, f"PC端容器宽度应该不超过680px，实际是{box['width']}px"
    print(f"   ✅ PC端布局正常 (宽度: {box['width']}px)")

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 启动 E2E 测试")
    print("=" * 60)

    # 启动服务器
    print("\n📡 启动服务器...")
    server = subprocess.Popen(
        ["python", "-m", "babysit.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # 等待服务器启动
        if not wait_for_server():
            print("❌ 服务器启动失败")
            return False
        print("✅ 服务器已启动\n")

        # 运行测试
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            tests = [
                test_baby_info,
                test_month_selector,
                test_summary_cards,
                test_heatmap,
                test_growth_section,
                test_vaccine_section,
                test_photo_section,
                test_quick_actions,
                test_responsive_layout,
            ]

            passed = 0
            failed = 0

            for test in tests:
                try:
                    test(page)
                    passed += 1
                except Exception as e:
                    failed += 1
                    print(f"   ❌ 测试失败: {e}")
                print()

            browser.close()

            # 打印结果
            print("=" * 60)
            print(f"📊 测试结果: {passed} 通过, {failed} 失败")
            print("=" * 60)

            return failed == 0

    finally:
        # 关闭服务器
        server.terminate()
        server.wait()
        print("\n📡 服务器已关闭")

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
