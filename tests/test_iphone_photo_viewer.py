from playwright.sync_api import sync_playwright


def swipe(page, start, end, steps=8):
    client = page.context.new_cdp_session(page)
    client.send("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": [{"x": start[0], "y": start[1], "id": 1}],
    })
    for index in range(1, steps + 1):
        x = start[0] + (end[0] - start[0]) * index / steps
        y = start[1] + (end[1] - start[1]) * index / steps
        client.send("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": [{"x": x, "y": y, "id": 1}],
        })
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_timeout(450)


def pinch(page, center, start_distance, end_distance, steps=6):
    client = page.context.new_cdp_session(page)
    cx, cy = center

    def points(distance):
        return [
            {"x": cx - distance / 2, "y": cy, "id": 1},
            {"x": cx + distance / 2, "y": cy, "id": 2},
        ]

    client.send("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": points(start_distance),
    })
    for index in range(1, steps + 1):
        distance = start_distance + (end_distance - start_distance) * index / steps
        client.send("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": points(distance),
        })
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_timeout(250)


def open_photo(page):
    import json
    from urllib.parse import quote

    page.goto("http://127.0.0.1:8765/2026/11", wait_until="domcontentloaded", timeout=15000)
    page.locator('.auth-input').fill('何与青')
    page.locator('.auth-btn').click()
    album = page.evaluate("async () => (await fetch('/api/album')).json()")
    candidates = []
    for date, files in album.items():
        static_files = [item for item in files if item.get("type") == "photo"]
        if static_files:
            candidates.append((date, static_files))
    assert candidates, "相册中没有可用于缩放测试的静态照片"
    candidates.sort(key=lambda item: (len(item[1]) > 1, item[0]), reverse=True)
    date, files = candidates[0]
    photo = files[0]
    page.goto(f"http://127.0.0.1:8765/{date[:4]}/{int(date[5:7])}", wait_until="domcontentloaded")
    image = page.locator(f'img[src*={json.dumps(quote(photo["name"]))}]').first
    image.wait_for(state="visible", timeout=15000)
    image.click()
    media = page.locator(".current-slide .slide-media")
    media.wait_for(state="visible", timeout=15000)
    media.evaluate("img => img.complete || (img.src = img.src)")
    page.wait_for_timeout(500)
    return media


def test_iphone_photo_viewer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            has_touch=True,
            is_mobile=True,
            service_workers="block",
        )
        page = context.new_page()
        media = open_photo(page)
        initial_index = page.locator(".photo-index").text_content()
        print("初始索引:", initial_index)

        swipe(page, (320, 400), (50, 400))
        next_index = page.locator(".photo-index").text_content()
        assert next_index != initial_index, "未缩放时左滑未翻页"
        print("左滑翻页通过:", next_index)

        media = page.locator(".current-slide .slide-media")
        media.dblclick()
        page.wait_for_timeout(300)
        assert page.locator(".slide-content.is-zoomed").count() == 1, "双击未放大"
        assert "scale(2.5)" in media.get_attribute("style")
        page.screenshot(path="test_iphone_zoom_mobile.png", full_page=True)

        pinch(page, (195, 400), 100, 170)
        assert "scale(4)" in media.get_attribute("style"), "双指缩放未达到预期"
        swipe(page, (195, 400), (255, 480))
        style = media.get_attribute("style")
        assert "translate(60px, 80px)" in style, f"放大后拖动位置不正确: {style}"
        print("双指缩放与单指拖动通过")

        zoomed_index = page.locator(".photo-index").text_content()
        swipe(page, (195, 250), (195, 700))
        assert page.locator(".viewer-overlay").is_visible(), "放大后下滑错误关闭了查看器"
        assert page.locator(".photo-index").text_content() == zoomed_index

        swipe(page, (300, 400), (60, 400))
        assert page.locator(".photo-index").text_content() == zoomed_index, "放大后横向手势触发了翻页"
        print("放大后上下关闭与翻页抑制通过")

        media.dblclick()
        page.wait_for_timeout(250)
        assert page.locator(".slide-content.is-zoomed").count() == 0, "双击未还原"
        swipe(page, (195, 250), (195, 700))
        assert page.locator(".viewer-overlay").count() == 0, "还原后下滑未关闭"
        print("还原后下滑关闭通过")
        context.close()

        desktop = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
        page = desktop.new_page()
        media = open_photo(page)
        assert page.locator(".nav-btn.next").is_visible()
        media.hover()
        page.mouse.wheel(0, -300)
        page.wait_for_timeout(250)
        assert page.locator(".slide-content.is-zoomed").count() == 1, "桌面滚轮未放大"
        page.screenshot(path="test_iphone_desktop.png", full_page=True)
        print("桌面导航按钮与滚轮缩放通过")
        browser.close()


if __name__ == "__main__":
    test_iphone_photo_viewer()
