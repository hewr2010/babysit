"""冷恢复压力自测：模拟微信与 H5 两条链路，跨月份点击 30+ 次并完整播放。

用法（需要 demo 服务运行）:
    .venv/bin/python tests/stress_cold_recovery.py [--base http://127.0.0.1:8080] [--h5]

Part A（默认，纯 HTTP，微信 UA）:
    模拟 previewMedia 行为：带 MicroMessenger UA 请求 /thumb /preview /video，
    校验 Content-Length、测量首字节/首 3MB 耗时（≈微信起播时间），并把下载到
    的字节喂给 ffprobe 验证 moov 在前、时长可解析——empty moov 这类「能下载
    不能播」的问题在这一步就会暴露。

Part B（--h5，Playwright 真实点击）:
    手机视口打开 H5，跨月份逐个点开媒体，视频完整播放到 ended（>30s 的用
    2 倍速），记录每次 TTFP 与异常（错误 UI、起播超时、播放停滞）。

退出码非 0 表示存在不合格项。
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

WECHAT_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) MicroMessenger/8.0.49"
MONTHS = ("2026/11", "2026/10")
TTFP_LIMIT = 5.0


def fetch_months(base):
    items = []
    for month in MONTHS:
        data = requests.get(f"{base}/api/album/{month}", timeout=15).json()
        for day, entries in data.items():
            for entry in entries:
                items.append({**entry, "month": month})
    return items


def probe_playable(payload, suffix):
    """把下载到的字节交给 ffprobe：时长可解析且能解出帧才算可播。"""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        path = handle.name
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=30,
        )
        if probe.returncode != 0:
            return False, "ffprobe 无法解析"
        duration = float(json.loads(probe.stdout)["format"].get("duration", 0))
        decode = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-f", "null", "-"],
            capture_output=True, timeout=60,
        )
        if decode.returncode != 0:
            return False, "首帧解码失败"
        return duration > 0, f"duration={duration:.1f}s" if duration > 0 else "时长为 0（empty moov?）"
    finally:
        Path(path).unlink(missing_ok=True)


def wechat_pass(base, items, rounds):
    results = []
    for round_index in range(rounds):
        for item in items:
            name = item["name"]
            is_video = item["type"] == "video"
            record = {"round": round_index + 1, "name": name, "type": item["type"], "ok": True, "notes": []}
            t0 = time.monotonic()
            url = f"{base}/{'video' if is_video else 'preview'}/{requests.utils.quote(name)}"
            try:
                response = requests.get(url, headers={"User-Agent": WECHAT_UA}, stream=True, timeout=40)
                record["status"] = response.status_code
                record["elapsed"] = round(time.monotonic() - t0, 2)
                if response.status_code != 200:
                    record["ok"] = False
                    body = response.raw.read(200).decode("utf-8", "replace")
                    record["notes"].append(f"HTTP {response.status_code} @{record['elapsed']}s {body[:80]}")
                    results.append(record)
                    continue
                if not response.headers.get("Content-Length"):
                    record["ok"] = False
                    record["notes"].append("缺少 Content-Length，微信无法起播")
                payload = b""
                t_first = None
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if t_first is None:
                        t_first = time.monotonic() - t0
                    payload += chunk
                    if len(payload) >= 3 * 1024 * 1024:
                        break
                response.close()
                record["t_first_byte"] = round(t_first or 0, 2)
                record["t_ready"] = round(time.monotonic() - t0, 2)
                # 微信起播需要 moov + 首个分片（1080p10M 下约 2MB）
                record["t_ttfp_proxy"] = round(time.monotonic() - t0, 2)
                if record["t_ttfp_proxy"] > TTFP_LIMIT:
                    record["ok"] = False
                    record["notes"].append(f"TTFP {record['t_ttfp_proxy']}s > {TTFP_LIMIT}s")
                if is_video:
                    playable, detail = probe_playable(payload, ".mp4")
                    record["notes"].append(detail)
                    if not playable:
                        record["ok"] = False
                else:
                    if not payload.startswith(b"\xff\xd8"):
                        record["ok"] = False
                        record["notes"].append("不是有效 JPEG")
            except requests.RequestException as error:
                record["ok"] = False
                record["notes"].append(f"请求失败: {error}")
            results.append(record)
            time.sleep(0.3)
    return results


def h5_pass(base):
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page.goto(base + "/")
        if page.locator("input.auth-input").count():
            page.fill("input.auth-input", "何与青")
            page.click("button.auth-btn")
            page.wait_for_timeout(800)
        for month in MONTHS:
            page.goto(f"{base}/{month}")
            page.wait_for_selector(".photo-item img", timeout=15000)
            page.wait_for_timeout(1200)
            names = page.evaluate(
                "() => [...document.querySelectorAll('.photo-item img')].map(i => decodeURIComponent(i.src.split('/thumb/')[1]))"
            )
            for name in names:
                record = {"month": month, "name": name, "ok": True, "notes": []}
                item = page.locator(f'.photo-item:has(img[src*="{requests.utils.quote(name)}"])').first
                t0 = time.monotonic()
                item.click()
                try:
                    page.wait_for_selector(".viewer-overlay .slide-media", timeout=10000)
                    is_video = page.locator(".viewer-overlay .current-slide video").count() > 0
                    deadline = time.monotonic() + 30
                    started = False
                    while time.monotonic() < deadline:
                        if page.locator(".slide-error").count():
                            record["ok"] = False
                            record["notes"].append("查看器报错: " + page.locator(".slide-error").inner_text())
                            break
                        state = page.evaluate(
                            """() => { const v = document.querySelector('.viewer-overlay .current-slide video');
                                if (v) return v.readyState >= 3 ? 'canplay' : 'waiting';
                                const i = document.querySelector('.viewer-overlay .current-slide img.slide-media');
                                return i && i.complete && i.naturalWidth > 0 ? 'canplay' : 'waiting' }"""
                        )
                        if state == "canplay":
                            started = True
                            break
                        time.sleep(0.2)
                    record["ttfp"] = round(time.monotonic() - t0, 2)
                    if not started:
                        record["ok"] = False
                        record["notes"].append("30s 未起播")
                    elif record["ttfp"] > TTFP_LIMIT:
                        record["notes"].append(f"TTFP {record['ttfp']}s 超 {TTFP_LIMIT}s（预恢复应覆盖，记录观察）")
                    if started and is_video:
                        duration = page.evaluate("() => document.querySelector('.viewer-overlay video').duration")
                        rate = 2.0 if (duration or 0) > 30 else 1.0
                        play_result = page.evaluate(
                            """async (rate) => { const v = document.querySelector('.viewer-overlay .current-slide video');
                                v.playbackRate = rate; v.muted = true;
                                try { await v.play() } catch (e) { return 'play() 失败: ' + e }
                                const t0 = Date.now(); let maxT = 0; let lastT = 0;
                                while (Date.now() - t0 < 240000) {
                                    await new Promise(r => setTimeout(r, 500));
                                    if (v.error) return '播放中出错 code=' + v.error.code;
                                    if (v.ended) return 'ended';
                                    if (v.currentTime > maxT) maxT = v.currentTime;
                                    if (v.duration && maxT >= v.duration * 0.98) return 'played-through';
                                    if (v.currentTime < lastT - 1 && maxT >= v.duration * 0.9) return 'played-through(loop)';
                                    lastT = v.currentTime;
                                }
                                return `超时未播完 maxT=${maxT.toFixed(1)}/${v.duration}`; }""",
                            rate,
                        )
                        record["notes"].append(f"播放: {play_result} (rate={rate})")
                        if play_result not in ("ended", "played-through", "played-through(loop)"):
                            record["ok"] = False
                except Exception as error:
                    record["ok"] = False
                    record["notes"].append(f"异常: {error}")
                finally:
                    if page.locator(".viewer-overlay .close-btn").count():
                        page.locator(".viewer-overlay .close-btn").click()
                        page.wait_for_timeout(400)
                results.append(record)
                print(f"  [{'OK' if record['ok'] else 'FAIL'}] {month} {name} "
                      f"ttfp={record.get('ttfp')} {'; '.join(record['notes'])}", flush=True)
        browser.close()
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8080")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--h5", action="store_true")
    args = parser.parse_args()

    items = fetch_months(args.base)
    print(f"共 {len(items)} 个媒体，微信链路 {args.rounds} 轮 = {len(items) * args.rounds} 次点击")
    wechat_results = wechat_pass(args.base, items, args.rounds)
    failures = [r for r in wechat_results if not r["ok"]]
    ttfp = sorted(r.get("t_ttfp_proxy", 0) for r in wechat_results if r["ok"])
    if ttfp:
        print(f"微信链路 TTFP: min={ttfp[0]}s 中位={ttfp[len(ttfp)//2]}s max={ttfp[-1]}s")
    for record in failures:
        print(f"  [FAIL] 轮{record['round']} {record['name']}: {'; '.join(record['notes'])}")

    h5_results = []
    if args.h5:
        print("H5 链路（真实点击 + 完整播放）:")
        h5_results = h5_pass(args.base)
        failures += [r for r in h5_results if not r["ok"]]

    print(f"\n总计 {len(wechat_results) + len(h5_results)} 次点击，异常 {len(failures)} 次")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
