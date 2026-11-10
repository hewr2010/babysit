import datetime
import functools
import http.server
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import urllib.parse

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = Path(tempfile.mkdtemp(prefix="babysit-h5-verify-"))


def main():
    print(f"H5 verification artifacts: {OUTPUT}")
    mock = subprocess.Popen(
        ["node", "-e", "require('./tests/mock-server').startMockServer().then(({port}) => console.log(port))"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        port = int(mock.stdout.readline().strip())
        env = {**os.environ, "VITE_API_HOST": f"http://127.0.0.1:{port}"}
        subprocess.run(["npm", "run", "build:h5"], cwd=ROOT, env=env, check=True)

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=str(ROOT / "dist" / "build" / "h5"),
        )
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                )
                page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_address[1]}/")
                expect(page.locator(".auth-card")).to_be_visible(timeout=15000)
                page.screenshot(path=OUTPUT / "01-auth.png", full_page=True)
                page.locator(".auth-input input").fill("何与青")
                page.locator(".auth-button").click()
                expect(page.locator(".growth-section")).to_be_visible(timeout=15000)
                page.screenshot(path=OUTPUT / "02-home.png", full_page=True)
                page.locator(".album-tab").click()
                expect(page.locator(".album-tab")).to_have_class("tab-item album-tab active")
                page.locator(".growth-tab").click()
                page.locator(".record-tab").click()
                expect(page.get_by_text("记录身高", exact=True).last).to_be_visible()
                expect(page.get_by_text("记录体重", exact=True).last).to_be_visible()
                page.get_by_text("记录身高", exact=True).last.click()
                expect(page.locator(".growth-value-input")).to_be_visible()
                page.locator(".sheet-close").click()
                expect(page.locator(".media-cell")).to_have_count(6)
                page.locator(".view-more-btn").click()
                expect(page.locator(".media-cell")).to_have_count(8)
                expect(page.locator(".view-more-btn")).to_have_text("收起")
                page.locator(".view-more-btn").click()
                expect(page.locator(".media-cell")).to_have_count(6)
                expect(page.locator(".album-hint")).to_have_count(0)
                page.locator(".media-menu-button").first.click()
                expect(page.locator(".album-actions")).to_be_visible()
                expect(page.locator(".action-share")).to_be_visible()
                expect(page.locator(".viewer-page")).to_have_count(0)
                page.locator(".open-milestone-editor").click()
                expect(page.locator(".milestone-title-input")).to_be_visible()
                page.locator(".sheet-close").click()
                page.locator(".media-cell").first.click()
                expect(page.locator(".viewer-page")).to_be_visible(timeout=10000)
                expect(page.locator(".viewer-share")).to_be_visible()
                expect(page.locator(".viewer-swiper")).to_be_visible()
                expect(page.locator(".zoom-view").first).to_be_visible()
                page.screenshot(path=OUTPUT / "03-viewer.png", full_page=True)
                page.locator(".viewer-page").dispatch_event("touchstart", {"touches": [{"identifier": 0, "clientX": 100, "clientY": 200}]})
                page.locator(".viewer-page").dispatch_event("touchend", {"changedTouches": [{"identifier": 0, "clientX": 220, "clientY": 200}]})
                expect(page.locator(".viewer-name")).to_have_text("第一张照片.jpg")
                page.locator(".viewer-swiper").evaluate("element => element.__vueParentComponent.emit('change', { detail: { current: 1 } })")
                expect(page.locator(".zoom-view .viewer-video")).to_be_visible(timeout=10000)
                expect(page.locator(".viewer-name")).to_have_text("第一段视频.mp4")
                assert page.locator(".viewer-video video").evaluate("video => video.loop") is False
                page.locator(".viewer-page").dispatch_event("touchstart", {"touches": [{"identifier": 0, "clientX": 180, "clientY": 200}]})
                page.locator(".viewer-page").dispatch_event("touchmove", {"touches": [{"identifier": 0, "clientX": 180, "clientY": 320}]})
                assert "translateY" in page.locator(".viewer-page").get_attribute("style")
                page.locator(".viewer-page").dispatch_event("touchend", {"changedTouches": [{"identifier": 0, "clientX": 180, "clientY": 340}]})
                expect(page.locator(".manage-milestones")).to_be_visible()
                page.locator(".manage-milestones").click()
                expect(page.locator(".manage-cell").first).to_be_visible(timeout=10000)
                page.screenshot(path=OUTPUT / "04-manage.png", full_page=True)

                now = datetime.datetime.now()
                shared_page = browser.new_page()
                shared_page.on("pageerror", lambda error: errors.append(str(error)))
                base_url = page.url.split("#")[0]
                media = urllib.parse.quote("第三张照片.jpg", safe="")
                shared_page.goto(f"{base_url}#/pages/viewer/viewer?media={media}&year={now.year}&month={now.month}")
                expect(shared_page.locator(".auth-card")).to_be_visible(timeout=10000)
                shared_page.locator(".auth-input input").fill("何与青")
                shared_page.locator(".auth-button").click()
                expect(shared_page.locator(".viewer-page")).to_be_visible(timeout=15000)
                expect(shared_page.locator(".viewer-name")).to_have_text("第三张照片.jpg")
                browser.close()
                if errors:
                    raise AssertionError("Browser errors:\n" + "\n".join(errors))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    finally:
        mock.terminate()
        mock.wait(timeout=10)
    print("H5 browser verification passed.")


if __name__ == "__main__":
    main()
