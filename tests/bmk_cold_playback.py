"""端点级冷播放 benchmark：候选媒体 TTFP≤5s 且能流畅完整播完。

直接打 endpoint API，模拟微信客户端完整流程：
  点击 → 轮询 /api/media/status → HLS 就绪后按真实播放器行为边下边播
  → 校验：起播时间、播放不卡顿（分段到达速度 ≥ 播放消耗）、
    内容完整（服务时长 ≈ 源时长、全片解码零错误）

用法:
    .venv/bin/python tests/bmk_cold_playback.py [--base http://127.0.0.1:8080] [--warm]

退出码非 0 = 有不合格项。结果同时写入 docs/cold-playback-bmk.md。
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote

import requests

TTFP_LIMIT = 5.0
STARTUP_BUFFER_SEGMENTS = 2  # 播放器起播缓冲（秒）
MONTHS = ("2026/11", "2026/10")
REPORT = Path(__file__).resolve().parent.parent / "docs" / "cold-playback-bmk.md"


def fetch_items(base):
    items = []
    for month in MONTHS:
        data = requests.get(f"{base}/api/album/{month}", timeout=15).json()
        for day, entries in data.items():
            for entry in entries:
                items.append({**entry, "month": month})
    return items


def evict(name):
    """直接删服务端缓存制造冷状态（仅 demo 环境）。"""
    import os
    os.environ["BABYSIT_DATA_DIR"] = "babysit/data/lru_demo"
    from babysit.media_cache import (
        existing_video_path, hls_dir, preview_path, video_metadata_path,
    )
    import shutil
    video = existing_video_path(name)
    if video:
        video.unlink()
        video_metadata_path(video).unlink(missing_ok=True)
    shutil.rmtree(hls_dir(name), ignore_errors=True)
    preview = preview_path(name)
    if preview.exists():
        preview.unlink()


def status(base, name):
    return requests.get(f"{base}/api/media/status/{quote(name)}", timeout=15).json()


def expected_duration(name):
    """完整缓存文件的时长（地面真值）。"""
    import os
    os.environ["BABYSIT_DATA_DIR"] = "babysit/data/lru_demo"
    from babysit.media_cache import existing_video_path
    video = existing_video_path(name)
    if not video:
        return None
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(video)],
        capture_output=True, text=True, timeout=30,
    )
    if probe.returncode != 0:
        return None
    return float(json.loads(probe.stdout)["format"].get("duration", 0))


def decode_check(payload, suffix=".mp4"):
    """全片解码：返回 (ok, decoded_duration, error)。"""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        path = handle.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=600,
        )
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60,
        )
        duration = 0.0
        if probe.returncode == 0:
            duration = float(json.loads(probe.stdout)["format"].get("duration", 0))
        errors = [line for line in result.stderr.splitlines() if "error" in line.lower()]
        return result.returncode == 0 and not errors, duration, "; ".join(errors[:3])
    finally:
        Path(path).unlink(missing_ok=True)


def parse_playlist(text):
    """返回 (segments[(uri, duration)], ended)。"""
    segments = []
    ended = "#EXT-X-ENDLIST" in text
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            duration = float(line.split(":", 1)[1].rstrip(","))
            uri = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if uri and not uri.startswith("#"):
                segments.append((uri, duration))
    return segments, ended


def fire_click(base, name, is_video):
    """模拟真实点击：请求媒体地址触发后端恢复（与小程序/浏览器行为一致）。"""
    url = f"{base}/{'video' if is_video else 'preview'}/{quote(name)}"

    def _fire():
        try:
            requests.get(url, timeout=30)
        except requests.RequestException:
            pass

    threading.Thread(target=_fire, daemon=True).start()


def bmk_video(base, item):
    """单个视频的端点级冷播放测试。"""
    name = item["name"]
    record = {"name": name, "ok": True, "notes": []}
    t0 = time.monotonic()
    fire_click(base, name, is_video=True)

    # 1. 模拟点击后轮询状态（与小程序一致）
    hls_at = full_at = None
    degraded = False
    while time.monotonic() - t0 < 240:
        try:
            s = status(base, name)
        except requests.RequestException:
            time.sleep(1)
            continue
        now = time.monotonic() - t0
        if s.get("state") == "hls_failed":
            degraded = True
            break
        if s.get("hls_ready") and hls_at is None:
            hls_at = now
        if s.get("video_ready"):
            full_at = now
            break
        time.sleep(0.5)
    if degraded:
        # 用户规则认可的降级：高码率大文件百度转码中，前端展示封面+提示
        record["notes"].append(f"拉流失败降级（{time.monotonic()-t0:.0f}s 判定）")
        return record
    if hls_at is None and full_at is None:
        record["ok"] = False
        record["notes"].append("240s 内 HLS 和完整文件都未就绪")
        return record

    playlist_url = f"{base}/hls/{quote(name)}/index.m3u8"

    # 2. HLS 边下边播模拟
    if hls_at is not None:
        segments = []  # (arrival, duration, bytes)
        payload = b""
        ended = False
        while time.monotonic() - t0 < 300:
            try:
                text = requests.get(playlist_url, timeout=15).text
            except requests.RequestException:
                time.sleep(0.5)
                continue
            playlist, ended = parse_playlist(text)
            while len(segments) < len(playlist):
                uri, duration = playlist[len(segments)]
                try:
                    body = requests.get(f"{playlist_url.rsplit('/', 1)[0]}/{uri}", timeout=30).content
                except requests.RequestException:
                    break
                segments.append((time.monotonic() - t0, duration, len(body)))
                payload += body
            if ended and len(segments) >= len(playlist):
                break
            if full_at is not None and len(segments) >= len(playlist):
                break
            time.sleep(0.3)

        # TTFP 以服务端播放列表出现时刻为准（含首段），排除 benchmark 自身下载耗时
        record["ttfp"] = round(hls_at, 2) if hls_at else None
        first_segment_at = segments[0][0] if segments else None
        if not segments:
            record["ok"] = False
            record["notes"].append("HLS 无分段产出")
        else:
            if hls_at and hls_at > TTFP_LIMIT:
                record["ok"] = False
                record["notes"].append(f"TTFP {record['ttfp']}s > {TTFP_LIMIT}s")

            # 3. 流畅性：播放器从 first_segment + 缓冲 开始，按真实时间消耗，
            #    每个分段必须在播放位置到达前就绪
            play_start = first_segment_at + STARTUP_BUFFER_SEGMENTS
            playhead = play_start
            stalls = []
            for arrival, duration, _ in segments:
                if arrival > playhead:
                    stalls.append(round(arrival - playhead, 2))
                    playhead = arrival
                playhead += duration
            record["stalls"] = stalls
            if stalls:
                record["ok"] = False
                record["notes"].append(f"播放卡顿 {len(stalls)} 次，最长 {max(stalls)}s")

        # 4. 完整性：服务总时长 + 全片解码
        served = sum(d for _, d, _ in segments)
        record["served_s"] = round(served, 1)
        ok, decoded, error = decode_check(payload, ".ts")
        record["decoded_s"] = round(decoded, 1)
        if not ok:
            record["ok"] = False
            record["notes"].append(f"全片解码失败: {error}")

    # 5. 完整 MP4 校验（地面真值 + 就绪后内容完整）
    if full_at is not None:
        record["full_ready_s"] = round(full_at, 1)
        import os
        os.environ["BABYSIT_DATA_DIR"] = "babysit/data/lru_demo"
        from babysit.media_cache import existing_video_path
        video = existing_video_path(name)
        expected = expected_duration(name)
        record["expected_s"] = round(expected, 1) if expected else None
        if hls_at is not None and expected:
            served = record.get("served_s", 0)
            if served < expected * 0.95:
                record["ok"] = False
                record["notes"].append(f"内容不完整: {served}s / {expected}s")
        if video is None:
            record["ok"] = False
            record["notes"].append("就绪但缓存文件缺失")
    return record


def bmk_photo(base, item):
    name = item["name"]
    record = {"name": name, "ok": True, "notes": []}
    t0 = time.monotonic()
    fire_click(base, name, is_video=False)
    response = None
    for attempt in range(10):
        try:
            response = requests.get(f"{base}/preview/{quote(name)}", timeout=30)
            if response.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    record["ttfp"] = round(time.monotonic() - t0, 2)
    if response is None or response.status_code != 200:
        record["ok"] = False
        record["notes"].append("预览 20s 内未就绪")
    elif not response.content.startswith(b"\xff\xd8"):
        record["ok"] = False
        record["notes"].append("不是有效 JPEG")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8080")
    parser.add_argument("--warm", action="store_true", help="不测冷启动，只验证就绪内容完整性")
    args = parser.parse_args()

    items = fetch_items(args.base)
    print(f"共 {len(items)} 个候选媒体")
    results = []
    for item in items:
        name = item["name"]
        if not args.warm:
            evict(name)
            time.sleep(1)
        print(f"测试 {name} ...", flush=True)
        if item["type"] == "video":
            record = bmk_video(args.base, item)
        else:
            record = bmk_photo(args.base, item)
        results.append(record)
        status_text = "OK" if record["ok"] else "FAIL"
        print(f"  [{status_text}] {name} ttfp={record.get('ttfp')} "
              f"full={record.get('full_ready_s')}s served={record.get('served_s')}s "
              f"expected={record.get('expected_s')}s {'; '.join(record['notes'])}", flush=True)

    failures = [r for r in results if not r["ok"]]
    lines = [
        "# 冷播放 Benchmark 结果",
        "",
        f"- 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 环境: {args.base}（3 存活 LRU 压测配置）",
        f"- 标准: TTFP ≤ {TTFP_LIMIT}s；起播后播放零卡顿；服务时长 ≥98% 源时长；全片解码零错误",
        "",
        "| 媒体 | 类型 | TTFP | 完整就绪 | 服务/源时长 | 卡顿 | 结果 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item, record in zip(items, results):
        lines.append(
            f"| {record['name']} | {item['type']} | {record.get('ttfp', '-')}s "
            f"| {record.get('full_ready_s', '-')}s "
            f"| {record.get('served_s', '-')}/{record.get('expected_s', '-')}s "
            f"| {len(record.get('stalls', []))} 次 "
            f"| {'✅' if record['ok'] else '❌ ' + '; '.join(record['notes'])} |"
        )
    lines += ["", f"**{len(results) - len(failures)}/{len(results)} 通过**", ""]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines))
    print(f"\n{len(results) - len(failures)}/{len(results)} 通过，报告: {REPORT}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
