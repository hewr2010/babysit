"""
后台媒体刷新进程

使用方法:
    python -m babysit.refresh_media

功能:
    - 每3分钟从百度网盘获取多媒体文件列表
    - 预处理所有多媒体文件（生成缩略图、预览图、提取视频等）
    - 只有完全完成预处理的文件才会在数据库中标记为可用
    - 通过 SQLite 数据库与前端应用通信可用文件列表
    - 使用 WAL 模式处理并发访问，避免 race condition
"""

import argparse
import io
import os
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener

# 注册 HEIF/HEIC 支持
register_heif_opener()

# 导入项目配置和数据库模块
from .config import CACHE_DIR, BAIDU_REMOTE_PATH, PCS_API_BASE, DATA_DIR
from .db import get_standalone_db, update_media_file, delete_media_file
from .media_cache import (
    claim_next_warm_job,
    enforce_cache_budget,
    existing_video_path,
    finish_warm_job,
    has_queued_warm_job,
    init_media_cache,
    original_livp_path,
    preview_path,
    record_cache_assets,
    thumbnail_path,
    update_warm_job_progress,
)

# 刷新间隔（秒）
REFRESH_INTERVAL = 3 * 60  # 3分钟

# 支持的文件扩展名
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".mp4", ".mov", ".heic", ".livp")
VIDEO_EXTS = (".mp4", ".mov", ".livp")


def get_access_token():
    """从 bypy 配置读取 token"""
    token_file = Path.home() / ".bypy" / "bypy.json"
    if not token_file.exists():
        return None
    with open(token_file) as f:
        import json

        return json.load(f).get("access_token")


def run_bypy(cmd, timeout=60):
    """运行 bypy 命令"""
    return subprocess.run(
        f"bypy {cmd}", shell=True, capture_output=True, text=True, timeout=timeout
    )


def extract_datetime_from_filename(filename):
    """从文件名提取拍摄日期和时间，返回(date_str, time_str)"""
    import re

    # 2026-03-01 101239.livp -> 2026-03-01, 10:12
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2})(\d{2})(\d{2})", filename)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        time_str = f"{match.group(4)}:{match.group(5)}"
        return date_str, time_str

    # IMG_20251220_100715.jpg -> 2025-12-20, 10:07
    match = re.search(
        r"(IMG|VID)_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", filename
    )
    if match:
        date_str = f"{match.group(2)}-{match.group(3)}-{match.group(4)}"
        time_str = f"{match.group(5)}:{match.group(6)}"
        return date_str, time_str

    # video_20260210_105828.mp4 -> 2026-02-10, 10:58
    match = re.search(r"video_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", filename)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        time_str = f"{match.group(4)}:{match.group(5)}"
        return date_str, time_str

    # mmexport1764123257729.jpg -> 从时间戳转换
    match = re.search(r"mmexport(\d{13})", filename)
    if match:
        timestamp_ms = int(match.group(1))
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

    return None, None


def extract_exif_datetime(img):
    """从EXIF数据提取拍摄日期和时间"""
    try:
        exif = img._getexif()
        if not exif:
            return None, None

        for tag_id, value in exif.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name in ("DateTimeOriginal", "DateTime"):
                if isinstance(value, str) and len(value) >= 19 and "\x00" not in value:
                    date_part = value[:10].replace(":", "-")
                    time_part = value[11:16]
                    if date_part != "0000-00-00" and date_part != "":
                        return date_part, time_part
        return None, None
    except:
        return None, None


def parse_bypy_list(output):
    """解析 bypy list 输出"""
    files = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("[") or line.startswith("<E>"):
            continue
        if line.startswith("F "):
            parts = line.split(" ")
            if len(parts) >= 5:
                size_idx = -1
                for i in range(1, len(parts)):
                    if parts[i].isdigit() and len(parts[i]) > 3:
                        size_idx = i
                        break

                if size_idx > 1:
                    filename = " ".join(parts[1:size_idx])
                    size = parts[size_idx]
                    baidu_date_str = parts[size_idx + 1].rstrip(",")

                    date_from_name, time_from_name = extract_datetime_from_filename(
                        filename
                    )
                    date_str = date_from_name if date_from_name else baidu_date_str

                    md5 = parts[-1] if len(parts) > size_idx + 3 else ""

                    files.append(
                        {
                            "name": filename,
                            "size": int(size),
                            "date": date_str,
                            "time": time_from_name or "",
                            "md5": md5,
                            "baidu_date": baidu_date_str,
                        }
                    )
    return files


def _get_download_url_once(filename):
    """获取一次百度网盘下载直链"""
    token = get_access_token()
    if not token:
        return None, "未授权"

    path = f"/apps/bypy{BAIDU_REMOTE_PATH}/{filename}"

    try:
        # 方法1: PCS API download 接口
        download_url = f"{PCS_API_BASE}?method=download&access_token={token}&path={quote(path, safe='')}"
        resp = requests.get(download_url, allow_redirects=False, timeout=10)

        if resp.status_code == 302:
            location = resp.headers.get("Location")
            if location:
                return location, None

        # 方法2: xpan 接口
        file_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=list&access_token={token}&dir={quote(f'/apps/bypy{BAIDU_REMOTE_PATH}', safe='')}"
        list_resp = requests.get(file_url, timeout=10)
        list_data = list_resp.json()

        if list_data.get("errno") == 0:
            file_list = list_data.get("list", [])
            target_file = None
            for f in file_list:
                if f.get("server_filename") == filename:
                    target_file = f
                    break

            if target_file:
                fs_id = target_file.get("fs_id")
                dlink_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemetas&access_token={token}&fsids=[{fs_id}]&dlink=1"
                dlink_resp = requests.get(dlink_url, timeout=10)
                dlink_data = dlink_resp.json()

                if dlink_data.get("errno") == 0:
                    file_info = dlink_data.get("list", [])
                    if file_info and file_info[0].get("dlink"):
                        dlink = file_info[0]["dlink"]
                        return f"{dlink}&access_token={token}", None

        return None, "无法获取下载链接"
    except Exception as e:
        print(f"Error getting download URL for {filename}: {e}")
        return None, str(e)


def get_download_url(filename):
    error = "无法获取下载链接"
    for attempt in range(3):
        url, error = _get_download_url_once(filename)
        if url:
            return url, None
        if attempt < 2:
            time.sleep(0.5 * (attempt + 1))
    return None, error


def _get_thumbnail_url_once(filename):
    token = get_access_token()
    if not token:
        return None
    directory = quote(f"/apps/bypy{BAIDU_REMOTE_PATH}", safe="")
    try:
        list_url = (
            "https://pan.baidu.com/rest/2.0/xpan/file?method=search"
            f"&access_token={token}&dir={directory}&recursion=0&num=20"
            f"&key={quote(filename, safe='')}"
        )
        files = requests.get(list_url, timeout=10).json().get("list", [])
        target = next((item for item in files if item.get("server_filename") == filename), None)
        if not target:
            return None
        meta_url = (
            "https://pan.baidu.com/rest/2.0/xpan/file?method=filemetas"
            f"&access_token={token}&fsids=[{target['fs_id']}]&thumb=1"
        )
        items = requests.get(meta_url, timeout=10).json().get("list", [])
        thumbs = items[0].get("thumbs", {}) if items else {}
        return thumbs.get("url3") or thumbs.get("url2") or thumbs.get("url1")
    except Exception as error:
        print(f"    ⚠️ 网盘缩略图不可用，回退原图: {error}")
        return None


def get_thumbnail_url(filename):
    for attempt in range(3):
        url = _get_thumbnail_url_once(filename)
        if url:
            return url
        if attempt < 2:
            time.sleep(0.5 * (attempt + 1))
    return None


def _download_to_file(url, dest_path, timeout=120, job_id=None):
    """流式下载文件到本地，避免把整个文件载入内存"""
    try:
        with requests.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            last_update = 0.0
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        if job_id and total and now - last_update >= 0.5:
                            update_warm_job_progress(
                                job_id, progress=round(downloaded / total * 100, 1), stage="下载",
                            )
                            last_update = now
        return True, None
    except Exception as e:
        print(f"    ❌ 下载失败: {e}")
        try:
            Path(dest_path).unlink(missing_ok=True)
        except Exception:
            pass
        return False, str(e)


def generate_image_thumbnail(img, size):
    """生成图片缩略图"""
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    output.seek(0)
    return output


def generate_video_thumbnail(video_path, size):
    """从本地视频文件提取第一帧并生成缩略图"""
    if not video_path.exists():
        return None

    temp_dir = CACHE_DIR / "temp_video"
    temp_dir.mkdir(exist_ok=True)
    temp_frame = temp_dir / f"{video_path.name}_frame.jpg"

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-q:v",
                "2",
                str(temp_frame),
            ],
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0 or not temp_frame.exists():
            return None

        with Image.open(temp_frame) as img:
            out = generate_image_thumbnail(img, size)

        temp_frame.unlink(missing_ok=True)
        return out
    except Exception as e:
        print(f"Error generating video thumbnail: {e}")
        temp_frame.unlink(missing_ok=True)
        return None


def extract_livp_video(video_data, filename):
    """从 .livp 文件中提取视频"""
    try:
        with zipfile.ZipFile(io.BytesIO(video_data), "r") as z:
            mov_name = None
            for name in z.namelist():
                if name.lower().endswith(".mov"):
                    mov_name = name
                    break

            if not mov_name:
                return None

            return z.read(mov_name)
    except Exception as e:
        print(f"Error extracting video from {filename}: {e}")
        return None


def _write_bytes_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.partial")
    try:
        with open(temp_path, "wb") as f:
            f.write(data)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def transcode_video(
    source_path, output_path, job_id=None, on_first_play=None,
    stop_after_first_play=False, abort_if=None,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_path.with_name(f".{output_path.name}.stream.mp4")
    temp_output.unlink(missing_ok=True)
    scale = "if(gt(iw,ih),min(iw,1280),-2)"
    is_remote = str(source_path).startswith(("http://", "https://"))
    source = "pipe:0" if is_remote else str(source_path)
    command = [
        "ffmpeg", "-y", "-analyzeduration", "1000000", "-probesize", "1000000",
        "-i", source, "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", f"scale=w='{scale}':h='{scale}'",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27", "-g", "60", "-keyint_min", "30",
        "-maxrate", "3M", "-bufsize", "6M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+frag_keyframe+empty_moov+default_base_moof",
        "-progress", "pipe:1", "-nostats", str(temp_output),
    ]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE if is_remote else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    process.stdout = io.TextIOWrapper(process.stdout, encoding="utf-8", errors="replace")
    process.stderr = io.TextIOWrapper(process.stderr, encoding="utf-8", errors="replace")
    duration = {"seconds": 0.0}
    errors = []

    def stream_remote_input():
        try:
            with requests.get(source_path, stream=True, timeout=(10, 30)) as response:
                errors.append(f"输入响应: {response.status_code} {response.headers.get('Content-Type')}")
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        process.stdin.write(chunk)
        except BrokenPipeError:
            pass
        except Exception as error:
            errors.append(f"网盘输入失败: {error}")
        finally:
            try:
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

    input_thread = threading.Thread(target=stream_remote_input, daemon=True) if is_remote else None
    if input_thread:
        input_thread.start()

    def read_errors():
        for line in process.stderr:
            if "Duration:" in line:
                try:
                    text = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
                    hours, minutes, seconds = text.split(":")
                    duration["seconds"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                except (ValueError, IndexError):
                    pass
            errors.append(line.strip())
            del errors[:-12]

    error_thread = threading.Thread(target=read_errors, daemon=True)
    error_thread.start()
    first_play = False
    progress = 0.0
    last_update = 0.0
    if job_id:
        update_warm_job_progress(job_id, progress=0, stage="转码", playback_ready=0)
    try:
        for line in process.stdout:
            if abort_if and abort_if():
                print("    ⏸️ 周期转码让位用户恢复请求")
                process.terminate()
                return False
            if not line.startswith("out_time_ms="):
                continue
            try:
                output_seconds = int(line.split("=", 1)[1]) / 1_000_000
            except ValueError:
                continue
            now = time.monotonic()
            if job_id and duration["seconds"] and now - last_update >= 0.5:
                progress = min(99, round(output_seconds / duration["seconds"] * 100, 1))
                update_warm_job_progress(job_id, progress=progress, stage="转码")
                last_update = now
            if not first_play and output_seconds >= 1.5 and temp_output.stat().st_size > 0:
                first_play = True
                if job_id:
                    update_warm_job_progress(
                        job_id, progress=progress if duration["seconds"] else None,
                        stage="可边下边播", playback_ready=1,
                    )
                if on_first_play:
                    on_first_play(temp_output)
                if stop_after_first_play:
                    process.terminate()
        return_code = process.wait()
        error_thread.join(timeout=2)
        if stop_after_first_play and first_play:
            return True
        if return_code != 0 or not temp_output.exists() or temp_output.stat().st_size == 0:
            print(f"    ❌ 视频转码失败: {'; '.join(errors)[-1500:]}")
            return False
        if not first_play and on_first_play:
            on_first_play(temp_output)
        os.replace(temp_output, output_path)
        if job_id:
            update_warm_job_progress(job_id, progress=100, stage="完成", playback_ready=1)
        return True
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
        if not stop_after_first_play:
            temp_output.unlink(missing_ok=True)


def process_streaming_video(
    file_info, thumbs_dir, previews_dir, videos_dir,
    job_id=None, on_first_play=None, stop_after_first_play=False, abort_if=None,
):
    filename = file_info["name"]
    safe_name = quote(filename, safe="")
    output_name = safe_name if filename.lower().endswith(".mp4") else f"{safe_name}.mp4"
    url, error = get_download_url(filename)
    if error or not url:
        return False, file_info

    def first_play(partial_path):
        for directory, size in ((thumbs_dir, (200, 200)), (previews_dir, (800, 800))):
            data = generate_video_thumbnail(partial_path, size)
            if data:
                suffix = "_200x200.jpg" if size == (200, 200) else "_800x800.jpg"
                _write_bytes_atomic(directory / f"{safe_name}{suffix}", data.getvalue())
        if on_first_play:
            on_first_play(partial_path)

    success = transcode_video(
        url, videos_dir / output_name, job_id=job_id,
        on_first_play=first_play, stop_after_first_play=stop_after_first_play,
        abort_if=abort_if,
    )
    if success:
        file_info["processed"] = True
        file_info["processed_at"] = datetime.now().isoformat()
    return success, file_info


def process_media_file(
    file_info, thumbs_dir, previews_dir, videos_dir, include_video=True,
    job_id=None, prefer_thumbnail=False, on_first_play=None,
    stop_after_first_play=False, abort_if=None,
):
    """生成永久缩略图、预览图和可选的视频播放派生文件。"""
    filename = file_info["name"]
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in VIDEO_EXTS

    print(f"  处理: {filename}")

    url = None
    if prefer_thumbnail and not is_video:
        url = get_thumbnail_url(filename)
    if not url:
        url, error = get_download_url(filename)
        if error or not url:
            print(f"    ❌ 无法获取下载链接: {error}")
            return False, file_info
    if is_video and include_video and ext in (".mp4", ".mov") and file_info.get("size", 0) >= 5 * 1024**2:
        return process_streaming_video(
            file_info, thumbs_dir, previews_dir, videos_dir, job_id,
            on_first_play, stop_after_first_play, abort_if,
        )

    temp_dir = CACHE_DIR / "temp_video"
    temp_dir.mkdir(parents=True, exist_ok=True)
    safe_name = quote(filename, safe="")
    temp_original = temp_dir / f"dl_{safe_name}"
    temp_video = None

    try:
        # 流式下载原始文件（视频不会进入内存）
        ok, err = _download_to_file(url, temp_original, job_id=job_id)
        if not ok:
            return False, file_info

        # 对 livp 先一次性解压出 mov；普通视频直接用下载好的临时文件
        if ext == ".livp":
            temp_video = temp_dir / f"{safe_name}.mov"
            try:
                with zipfile.ZipFile(temp_original, "r") as z:
                    mov_name = None
                    for name in z.namelist():
                        if name.lower().endswith(".mov"):
                            mov_name = name
                            break

                    if not mov_name:
                        print(f"    ❌ livp 中未找到 mov")
                        return False, file_info

                    with open(temp_video, "wb") as out_f:
                        with z.open(mov_name) as src:
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                out_f.write(chunk)
            except zipfile.BadZipFile:
                print(f"    ❌ livp 文件损坏")
                return False, file_info
        elif is_video:
            temp_video = temp_original

        # 生成缩略图 (200x200)
        thumb_path = thumbs_dir / f"{safe_name}_200x200.jpg"
        if is_video:
            thumb_data = generate_video_thumbnail(temp_video, (200, 200))
        else:
            with Image.open(temp_original) as img:
                exif_date, exif_time = extract_exif_datetime(img)
                if exif_date and exif_date != "0000-00-00":
                    file_info["date"] = exif_date
                    file_info["time"] = exif_time or file_info.get("time", "")
                thumb_data = generate_image_thumbnail(img, (200, 200))

        if thumb_data:
            _write_bytes_atomic(thumb_path, thumb_data.getvalue())
            print(f"    ✓ 缩略图已生成")
        else:
            print(f"    ❌ 缩略图生成失败")
            return False, file_info

        preview_path = previews_dir / f"{safe_name}_800x800.jpg"
        if is_video:
            preview_data = generate_video_thumbnail(temp_video, (800, 800))
        else:
            with Image.open(temp_original) as img:
                preview_data = generate_image_thumbnail(img, (800, 800))

        if preview_data:
            _write_bytes_atomic(preview_path, preview_data.getvalue())
            print(f"    ✓ 预览图已生成")
        else:
            print(f"    ❌ 预览图生成失败")
            return False, file_info

        if is_video and include_video:
            output_name = safe_name if ext == ".mp4" else f"{safe_name}.mp4"
            video_cache_path = videos_dir / output_name
            if not transcode_video(
                temp_video, video_cache_path, job_id=job_id,
                on_first_play=on_first_play,
                stop_after_first_play=stop_after_first_play,
                abort_if=abort_if,
            ):
                return False, file_info
            if ext == ".livp":
                (videos_dir / f"{safe_name}.mov").unlink(missing_ok=True)
            elif ext == ".mov":
                (videos_dir / safe_name).unlink(missing_ok=True)
            print(f"    ✓ 视频已压缩缓存")

        file_info["processed"] = True
        file_info["processed_at"] = datetime.now().isoformat()
        if on_first_play and not is_video:
            on_first_play(preview_path)
        print(f"    ✓ 处理完成")
        return True, file_info

    except Exception as e:
        print(f"    ❌ 处理异常: {e}")
        return False, file_info

    finally:
        for p in (temp_original, temp_video):
            if p:
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass


def refresh_media():
    """执行一次媒体刷新操作"""
    print(f"\n{'=' * 60}")
    print(f"🔄 开始媒体刷新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    # 创建必要的目录
    thumbs_dir = CACHE_DIR / "thumbs"
    previews_dir = CACHE_DIR / "previews"
    videos_dir = CACHE_DIR / "videos"
    for d in [thumbs_dir, previews_dir, videos_dir]:
        d.mkdir(exist_ok=True)

    # 从百度网盘获取文件列表
    print(f"\n📥 从百度网盘获取文件列表...")
    result = run_bypy(f"list '{BAIDU_REMOTE_PATH}'")

    if result.returncode != 0:
        print(f"❌ 获取文件列表失败: {result.stderr}")
        return

    # 解析文件列表
    baidu_files = parse_bypy_list(result.stdout)

    # 过滤支持的文件类型
    media_files = []
    for f in baidu_files:
        ext = os.path.splitext(f["name"])[1].lower()
        if ext in SUPPORTED_EXTS:
            f["type"] = "video" if ext in VIDEO_EXTS else "photo"
            f["processed"] = False
            media_files.append(f)
    media_files.sort(key=lambda x: x["name"], reverse=True)

    print(f"📊 找到 {len(media_files)} 个多媒体文件")

    # 获取数据库连接
    db = get_standalone_db()

    try:
        # 处理每个文件
        new_count = 0
        updated_count = 0
        failed_count = 0
        current_names = set()
        hot_cutoff = datetime.fromtimestamp(time.time() - 30 * 86400).date().isoformat()

        for file_info in media_files:
            if has_queued_warm_job():
                process_one_warm_job()
            filename = file_info["name"]
            ext = os.path.splitext(filename)[1].lower()
            md5 = file_info.get("md5", "")
            current_names.add(filename)

            cursor = db.execute(
                "SELECT md5, processed FROM media_files WHERE filename = ?", (filename,)
            )
            existing = cursor.fetchone()

            if existing and existing["md5"] == md5 and existing["processed"]:
                if thumbnail_path(filename, CACHE_DIR).is_file():
                    is_hot = file_info["date"] >= hot_cutoff
                    preview_ready = preview_path(filename, CACHE_DIR).is_file()
                    video_ready = ext not in VIDEO_EXTS or existing_video_path(filename, CACHE_DIR)
                    if not is_hot or (preview_ready and video_ready):
                        record_cache_assets(filename)
                        continue
                else:
                    print(f"  ⚠️ {filename} 的永久缩略图缺失，需要重新处理")

            success, updated_info = process_media_file(
                file_info,
                thumbs_dir,
                previews_dir,
                videos_dir,
                include_video=ext not in VIDEO_EXTS or file_info["date"] >= hot_cutoff,
                abort_if=has_queued_warm_job,
            )

            if success:
                update_media_file(db, updated_info)
                db.commit()
                record_cache_assets(filename)

                if existing is None:
                    new_count += 1
                else:
                    updated_count += 1
            else:
                failed_count += 1
                # 如果处理失败，不更新记录（保留旧的已处理记录）

        # 清理不存在的文件记录
        cursor = db.execute("SELECT filename FROM media_files")
        db_names = {row["filename"] for row in cursor.fetchall()}
        removed = db_names - current_names

        for name in removed:
            delete_media_file(db, name)

        if removed:
            db.commit()
            print(f"\n🗑️  清理了 {len(removed)} 个不存在的文件记录")

        # 统计
        cursor = db.execute("SELECT COUNT(*) FROM media_files WHERE processed = 1")
        total_available = cursor.fetchone()[0]

    finally:
        db.close()

    print(f"\n{'=' * 60}")
    print(f"✅ 刷新完成")
    print(f"   新增: {new_count}")
    print(f"   更新: {updated_count}")
    print(f"   失败: {failed_count}")
    print(f"   总计可用: {total_available}")
    print(f"{'=' * 60}\n")


def repair_media_database():
    """修复永久缩略图与媒体记录的一致性，不把冷缓存误判为未处理。"""
    db = get_standalone_db()
    reset_count = 0
    set_processed_count = 0
    cleaned_bytes = 0
    try:
        rows = db.execute("SELECT filename, processed FROM media_files").fetchall()
        for row in rows:
            filename = row["filename"]
            thumb = thumbnail_path(filename, CACHE_DIR)
            thumb_ready = thumb.is_file() and thumb.stat().st_size > 0
            if thumb_ready and not row["processed"]:
                db.execute(
                    "UPDATE media_files SET processed = 1, "
                    "processed_at = CURRENT_TIMESTAMP WHERE filename = ?",
                    (filename,),
                )
                set_processed_count += 1
            elif not thumb_ready and row["processed"]:
                db.execute(
                    "UPDATE media_files SET processed = 0, processed_at = NULL "
                    "WHERE filename = ?",
                    (filename,),
                )
                thumb.unlink(missing_ok=True)
                reset_count += 1
        db.commit()

        temp_dir = CACHE_DIR / "temp_video"
        if temp_dir.exists():
            for path in temp_dir.iterdir():
                if path.is_file():
                    cleaned_bytes += path.stat().st_size
                    path.unlink(missing_ok=True)
        print(
            f"修复完成: 重置 {reset_count} 条，补标记 {set_processed_count} 条，"
            f"清理 {cleaned_bytes / 1024 / 1024:.2f} MB"
        )
    finally:
        db.close()


def process_original_livp(file_info):
    filename = file_info["name"]
    url, error = get_download_url(filename)
    if error or not url:
        return False
    temp_dir = CACHE_DIR / "temp_video"
    temp_dir.mkdir(parents=True, exist_ok=True)
    source = temp_dir / f"original-{quote(filename, safe='')}"
    output = original_livp_path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f".{output.name}.partial")
    try:
        success, _ = _download_to_file(url, source)
        if not success:
            return False
        with zipfile.ZipFile(source) as archive:
            mov_name = next((name for name in archive.namelist() if name.lower().endswith(".mov")), None)
            if not mov_name:
                return False
            with archive.open(mov_name) as src, open(temp_output, "wb") as dst:
                while True:
                    chunk = src.read(256 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
        os.replace(temp_output, output)
        return True
    except (OSError, zipfile.BadZipFile) as error:
        print(f"    ❌ Live Photo 原件解包失败: {error}")
        return False
    finally:
        source.unlink(missing_ok=True)
        temp_output.unlink(missing_ok=True)


def process_one_warm_job():
    job = claim_next_warm_job()
    if not job:
        return False
    db = get_standalone_db()
    try:
        row = db.execute(
            "SELECT * FROM media_files WHERE filename = ? AND processed = 1",
            (job["filename"],),
        ).fetchone()
    finally:
        db.close()
    if not row:
        finish_warm_job(job["id"], "媒体已不存在")
        return True
    file_info = {
        "name": row["filename"],
        "type": row["file_type"],
        "size": row["file_size"],
        "md5": row["md5"],
        "date": row["date"],
        "time": row["time"] or "",
        "baidu_date": row["baidu_date"] or "",
        "processed": True,
    }
    if job["kind"] == "original_livp":
        try:
            if not process_original_livp(file_info):
                raise RuntimeError("Live Photo 原件下载或解包失败")
            finish_warm_job(job["id"])
        except Exception as error:
            finish_warm_job(job["id"], str(error))
        return True
    try:
        required = row["file_size"] or 0 if job["kind"] == "video" else 0
        budget = enforce_cache_budget(required_bytes=required)
        if not budget["within_budget"]:
            raise RuntimeError("热数据已超过缓存容量，无法继续恢复")
        success, _ = process_media_file(
            file_info,
            CACHE_DIR / "thumbs",
            CACHE_DIR / "previews",
            CACHE_DIR / "videos",
            include_video=job["kind"] == "video",
            job_id=job["id"],
            prefer_thumbnail=False,
        )
        if not success:
            raise RuntimeError("网盘下载或媒体处理失败")
        record_cache_assets(job["filename"])
        finish_warm_job(job["id"])
    except Exception as error:
        finish_warm_job(job["id"], str(error))
    return True


def main():
    print("媒体刷新与缓存恢复服务启动")
    init_media_cache()
    next_refresh = 0
    while True:
        if time.time() >= next_refresh:
            try:
                refresh_media()
                enforce_cache_budget()
            except Exception as error:
                print(f"刷新失败: {error}")
            next_refresh = time.time() + REFRESH_INTERVAL
        if not process_one_warm_job():
            time.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="后台媒体刷新服务")
    parser.add_argument(
        "--repair", action="store_true", help="修复数据库与缓存的不一致后退出"
    )
    args = parser.parse_args()

    if args.repair:
        try:
            repair_media_database()
        except KeyboardInterrupt:
            print("\n\n👋 已中断")
        sys.exit(0)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
        sys.exit(0)
