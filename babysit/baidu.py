"""百度网盘模块"""
import json
import subprocess
import io
import os
import time
import threading
import queue
from pathlib import Path
from urllib.parse import quote, unquote
import requests
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
from .config import CACHE_DIR, BAIDU_REMOTE_PATH, PCS_API_BASE

# 注册 HEIF/HEIC 支持
register_heif_opener()

# 线程锁用于缓存操作
_cache_lock = threading.Lock()

# 处理状态追踪: {filename: {'thumb_200': 'pending'|'processing'|'done'|'error', 'thumb_800': ..., 'video': ...}}
_processing_status = {}
_processing_lock = threading.Lock()

# SSE 客户端队列列表
_sse_clients = []
_sse_lock = threading.Lock()


def _get_status_key(filename, size):
    """生成状态键"""
    if size == (200, 200):
        return 'thumb_200'
    elif size == (800, 800):
        return 'thumb_800'
    return f'thumb_{size[0]}x{size[1]}'


def _notify_sse_clients(filename, status_update):
    """通知所有 SSE 客户端状态变更"""
    with _sse_lock:
        dead_clients = []
        for client_queue in _sse_clients:
            try:
                client_queue.put_nowait({
                    'filename': filename,
                    'status': status_update,
                    'timestamp': time.time()
                })
            except queue.Full:
                dead_clients.append(client_queue)
        
        # 清理已失效的客户端
        for dead in dead_clients:
            if dead in _sse_clients:
                _sse_clients.remove(dead)


def register_sse_client():
    """注册一个新的 SSE 客户端，返回消息队列"""
    q = queue.Queue(maxsize=100)
    with _sse_lock:
        _sse_clients.append(q)
    return q


def unregister_sse_client(q):
    """注销 SSE 客户端"""
    with _sse_lock:
        if q in _sse_clients:
            _sse_clients.remove(q)


def set_processing_status(filename, key, status, notify=True):
    """设置处理状态"""
    with _processing_lock:
        if filename not in _processing_status:
            _processing_status[filename] = {}
        _processing_status[filename][key] = status
        _processing_status[filename]['_updated'] = time.time()
    
    # 通知 SSE 客户端
    if notify:
        _notify_sse_clients(filename, {key: status})


def get_processing_status(filename):
    """获取文件处理状态"""
    with _processing_lock:
        status = _processing_status.get(filename, {}).copy()
    
    # 检查实际缓存文件是否存在
    for size in [(200, 200), (800, 800)]:
        cache_key = f"{filename}_{size[0]}x{size[1]}"
        cache_file = CACHE_DIR / "thumbs" / f"{quote(cache_key, safe='')}.jpg"
        key = _get_status_key(filename, size)
        if cache_file.exists():
            status[key] = 'done'
        elif key not in status:
            status[key] = 'pending'
    
    # 视频文件额外检查
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.livp':
        cache_key = f"{filename}_video"
        cache_file = CACHE_DIR / "livp_videos" / f"{quote(cache_key, safe='')}.mov"
        if cache_file.exists():
            status['video'] = 'done'
        elif 'video' not in status:
            status['video'] = 'pending'
    
    return status


def get_access_token():
    """从 bypy 配置读取 token"""
    token_file = Path.home() / ".bypy" / "bypy.json"
    if not token_file.exists():
        return None
    with open(token_file) as f:
        return json.load(f).get('access_token')


def run_bypy(cmd, timeout=60):
    return subprocess.run(
        f"bypy {cmd}", shell=True, capture_output=True, text=True, timeout=timeout
    )


def extract_datetime_from_filename(filename):
    """从文件名提取拍摄日期和时间，返回(date_str, time_str)"""
    import re
    from datetime import datetime
    
    # 2026-03-01 101239.livp -> 2026-03-01, 10:12
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2}) (\d{2})(\d{2})(\d{2})', filename)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        time_str = f"{match.group(4)}:{match.group(5)}"
        return date_str, time_str
    
    # IMG_20251220_100715.jpg -> 2025-12-20, 10:07
    match = re.search(r'(IMG|VID)_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
    if match:
        date_str = f"{match.group(2)}-{match.group(3)}-{match.group(4)}"
        time_str = f"{match.group(5)}:{match.group(6)}"
        return date_str, time_str
    
    # video_20260210_105828.mp4 -> 2026-02-10, 10:58
    match = re.search(r'video_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        time_str = f"{match.group(4)}:{match.group(5)}"
        return date_str, time_str
    
    # mmexport1764123257729.jpg -> 从时间戳转换
    match = re.search(r'mmexport(\d{13})', filename)
    if match:
        timestamp_ms = int(match.group(1))
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    
    return None, None


def extract_date_from_filename(filename):
    """从文件名提取拍摄日期"""
    date_str, _ = extract_datetime_from_filename(filename)
    return date_str


def extract_exif_datetime(img):
    """从EXIF数据提取拍摄日期和时间"""
    try:
        exif = img._getexif()
        if not exif:
            return None, None
        
        for tag_id, value in exif.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name in ('DateTimeOriginal', 'DateTime'):
                if isinstance(value, str) and len(value) >= 19:
                    date_part = value[:10].replace(':', '-')
                    time_part = value[11:16]
                    if date_part != '0000-00-00' and date_part != '':
                        return date_part, time_part
        return None, None
    except:
        return None, None


def get_exif_cache():
    """读取EXIF时间缓存"""
    cache_file = CACHE_DIR / "exif_times.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    return {}


def save_exif_cache(cache):
    """保存EXIF时间缓存"""
    cache_file = CACHE_DIR / "exif_times.json"
    with open(cache_file, 'w') as f:
        json.dump(cache, f)


def parse_bypy_list(output):
    """解析 bypy list 输出"""
    files = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('[') or line.startswith('<E>'):
            continue
        if line.startswith('F '):
            parts = line.split(' ')
            if len(parts) >= 5:
                size_idx = -1
                for i in range(1, len(parts)):
                    if parts[i].isdigit() and len(parts[i]) > 3:
                        size_idx = i
                        break
                
                if size_idx > 1:
                    filename = ' '.join(parts[1:size_idx])
                    size = parts[size_idx]
                    baidu_date_str = parts[size_idx + 1].rstrip(',')
                    date_from_name, time_from_name = extract_datetime_from_filename(filename)
                    date_str = date_from_name if date_from_name else baidu_date_str
                    md5 = parts[-1] if len(parts) > size_idx + 3 else ''
                    
                    files.append({
                        'name': filename,
                        'size': size,
                        'date': date_str,
                        'time': time_from_name or '',
                        'md5': md5,
                        'baidu_date': baidu_date_str
                    })
    return files


def get_baidu_files(force_refresh=False):
    """获取百度网盘文件，按日期分组"""
    cache_file = CACHE_DIR / "baidu_files.json"
    
    if not force_refresh and cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            return update_files_with_exif(data)
    
    result = run_bypy(f"list '{BAIDU_REMOTE_PATH}'")
    if result.returncode != 0:
        return {}
    
    files = []
    for f in parse_bypy_list(result.stdout):
        ext = os.path.splitext(f['name'])[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.livp'):
            f['type'] = 'video' if ext in ('.mp4', '.mov', '.livp') else 'photo'
            files.append(f)
    
    date_groups = {}
    for f in files:
        d = f['date']
        if d not in date_groups:
            date_groups[d] = []
        date_groups[d].append(f)
    
    for d in date_groups:
        date_groups[d].sort(key=lambda x: x.get('time', ''), reverse=True)
    
    sorted_groups = dict(sorted(date_groups.items(), key=lambda x: x[0], reverse=True))
    
    with open(cache_file, 'w') as f:
        json.dump(sorted_groups, f)
    
    return update_files_with_exif(sorted_groups)


def update_files_with_exif(date_groups):
    """使EXIF缓存更新文件日期时间"""
    exif_cache = get_exif_cache()
    if not exif_cache:
        return date_groups
    
    new_groups = {}
    for date_str, files in date_groups.items():
        for f in files:
            filename = f['name']
            if filename in exif_cache:
                f['date'] = exif_cache[filename]['date']
                f['time'] = exif_cache[filename]['time']
            
            d = f['date']
            if d not in new_groups:
                new_groups[d] = []
            new_groups[d].append(f)
    
    for d in new_groups:
        new_groups[d].sort(key=lambda x: x.get('time', ''), reverse=True)
    
    sorted_groups = dict(sorted(new_groups.items(), key=lambda x: x[0], reverse=True))
    return sorted_groups


def get_download_url(filename):
    """获取百度网盘下载直链"""
    token = get_access_token()
    if not token:
        return None, "未授权"
    
    path = f'/apps/bypy{BAIDU_REMOTE_PATH}/{filename}'
    
    try:
        download_url = f"{PCS_API_BASE}?method=download&access_token={token}&path={quote(path, safe='')}"
        resp = requests.get(download_url, allow_redirects=False, timeout=10)
        
        if resp.status_code == 302:
            location = resp.headers.get('Location')
            if location:
                return location, None
        
        file_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=list&access_token={token}&dir={quote(f'/apps/bypy{BAIDU_REMOTE_PATH}', safe='')}"
        list_resp = requests.get(file_url, timeout=10)
        list_data = list_resp.json()
        
        if list_data.get('errno') == 0:
            file_list = list_data.get('list', [])
            target_file = None
            for f in file_list:
                if f.get('server_filename') == filename:
                    target_file = f
                    break
            
            if target_file:
                fs_id = target_file.get('fs_id')
                dlink_url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemetas&access_token={token}&fsids=[{fs_id}]&dlink=1"
                dlink_resp = requests.get(dlink_url, timeout=10)
                dlink_data = dlink_resp.json()
                
                if dlink_data.get('errno') == 0:
                    file_info = dlink_data.get('list', [])
                    if file_info and file_info[0].get('dlink'):
                        dlink = file_info[0]['dlink']
                        return f"{dlink}&access_token={token}", None
        
        return None, "无法获取下载链接"
    except Exception as e:
        print(f"Error getting download URL for {filename}: {e}")
        return None, str(e)


def extract_livp_video(filename):
    """从 .livp 文件中提取视频部分"""
    ext = os.path.splitext(filename)[1].lower()
    if ext != '.livp':
        return None
    
    cache_key = f"{filename}_video"
    cache_file = CACHE_DIR / "livp_videos" / f"{quote(cache_key, safe='')}.mov"
    cache_file.parent.mkdir(exist_ok=True)
    
    if cache_file.exists():
        set_processing_status(filename, 'video', 'done')
        with open(cache_file, 'rb') as f:
            return io.BytesIO(f.read())
    
    current_status = get_processing_status(filename).get('video')
    if current_status == 'processing':
        return None
    
    def download_and_extract():
        set_processing_status(filename, 'video', 'processing')
        print(f"[Video] Start extracting video from: {filename}")
        try:
            url, err = get_download_url(filename)
            if err or not url:
                print(f"[Video] Failed to get download URL: {filename}")
                set_processing_status(filename, 'video', 'error')
                return None
            
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                print(f"[Video] Failed to download: {filename}")
                set_processing_status(filename, 'video', 'error')
                return None
            
            import zipfile
            with zipfile.ZipFile(io.BytesIO(resp.content), 'r') as z:
                mov_name = None
                for name in z.namelist():
                    if name.lower().endswith('.mov'):
                        mov_name = name
                        break
                
                if not mov_name:
                    print(f"[Video] No MOV file found in: {filename}")
                    set_processing_status(filename, 'video', 'error')
                    return None
                
                mov_data = z.read(mov_name)
                with open(cache_file, 'wb') as f:
                    f.write(mov_data)
                
                print(f"[Video] ✓ Extracted: {filename} ({len(mov_data)} bytes)")
                set_processing_status(filename, 'video', 'done')
                return io.BytesIO(mov_data)
        except Exception as e:
            print(f"[Video] ✗ Error extracting video from {filename}: {e}")
            set_processing_status(filename, 'video', 'error')
            return None
    
    thread = threading.Thread(target=download_and_extract, daemon=True)
    thread.start()
    set_processing_status(filename, 'video', 'processing')
    return None


def get_thumbnail_data(filename, size=(200, 200)):
    """获取缩略图数据（图片或视频封面）- 使用后台线程处理"""
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in ('.mp4', '.mov', '.livp')
    status_key = _get_status_key(filename, size)
    size_label = f"{size[0]}x{size[1]}"
    
    cache_key = f"{filename}_{size[0]}x{size[1]}"
    cache_file = CACHE_DIR / "thumbs" / f"{quote(cache_key, safe='')}.jpg"
    cache_file.parent.mkdir(exist_ok=True)
    
    if cache_file.exists():
        set_processing_status(filename, status_key, 'done')
        with open(cache_file, 'rb') as f:
            return io.BytesIO(f.read())
    
    current_status = get_processing_status(filename).get(status_key)
    if current_status == 'processing':
        return None
    
    def generate_thumb():
        set_processing_status(filename, status_key, 'processing')
        print(f"[Thumb-{size_label}] Start generating: {filename}")
        try:
            result = _generate_thumbnail_internal(filename, size, is_video, ext, cache_file)
            if result:
                print(f"[Thumb-{size_label}] ✓ Done: {filename}")
                set_processing_status(filename, status_key, 'done')
            else:
                print(f"[Thumb-{size_label}] ✗ Failed: {filename}")
                set_processing_status(filename, status_key, 'error')
        except Exception as e:
            print(f"[Thumb-{size_label}] ✗ Error for {filename}: {e}")
            set_processing_status(filename, status_key, 'error')
    
    thread = threading.Thread(target=generate_thumb, daemon=True)
    thread.start()
    set_processing_status(filename, status_key, 'processing')
    return None


def _generate_thumbnail_internal(filename, size, is_video, ext, cache_file, _size_label=None):
    """内部方法：实际生成缩略图"""
    size_label = _size_label or f"{size[0]}x{size[1]}"
    print(f"[Thumb-{size_label}] Processing: {filename}")
    
    url, err = get_download_url(filename)
    if err or not url:
        print(f"[Thumb-{size_label}] ✗ No download URL: {filename}")
        return None
    
    try:
        if is_video:
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                return None
            
            temp_video = CACHE_DIR / "temp_video"
            temp_video.mkdir(exist_ok=True)
            
            if ext == '.livp':
                import zipfile
                try:
                    with zipfile.ZipFile(io.BytesIO(resp.content), 'r') as z:
                        mov_name = None
                        for name in z.namelist():
                            if name.lower().endswith('.mov'):
                                mov_name = name
                                break
                        
                        if not mov_name:
                            return None
                        
                        video_path = temp_video / f"{filename}.mov"
                        with open(video_path, 'wb') as f:
                            f.write(z.read(mov_name))
                except zipfile.BadZipFile:
                    return None
            else:
                video_path = temp_video / filename
                with open(video_path, 'wb') as f:
                    f.write(resp.content)
            
            temp_frame = temp_video / f"{filename}_frame.jpg"
            result = subprocess.run(
                ['ffmpeg', '-i', str(video_path), '-vframes', '1', '-q:v', '2', str(temp_frame)],
                capture_output=True,
                timeout=30
            )
            
            video_path.unlink(missing_ok=True)
            
            if result.returncode != 0 or not temp_frame.exists():
                return None
            
            img = Image.open(temp_frame)
            temp_frame.unlink(missing_ok=True)
        else:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return None
                
            img = Image.open(io.BytesIO(resp.content))
            
            if size == (200, 200):
                date_str, time_str = extract_exif_datetime(img)
                if not date_str or date_str == '0000-00-00':
                    cache_file_path = CACHE_DIR / "baidu_files.json"
                    if cache_file_path.exists():
                        import json
                        with open(cache_file_path) as f:
                            all_files = json.load(f)
                            for date, file_list in all_files.items():
                                for f_info in file_list:
                                    if f_info['name'] == filename:
                                        date_str = f_info.get('baidu_date') or f_info.get('date', '')
                                        time_str = ''
                                        break
                                if date_str:
                                    break
                
                if date_str:
                    with _cache_lock:
                        exif_cache = get_exif_cache()
                        exif_cache[filename] = {'date': date_str, 'time': time_str or ''}
                        save_exif_cache(exif_cache)
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        with open(cache_file, 'wb') as f:
            f.write(output.getvalue())
        output.seek(0)
        print(f"[Thumb-{size_label}] ✓ Saved: {filename}")
        
        # 更新状态并通知前端
        status_key = _get_status_key(filename, size)
        set_processing_status(filename, status_key, 'done')
        
        return output
    except Exception as e:
        print(f"[Thumb-{size_label}] ✗ Error: {filename} - {e}")
        # 更新状态为错误
        status_key = _get_status_key(filename, size)
        set_processing_status(filename, status_key, 'error')
        return None


def prefetch_thumbnails(files_by_date, max_workers=4):
    """预生成所有文件的缩略图（用于后台任务）"""
    all_files = []
    for date_str, files in files_by_date.items():
        for f in files:
            all_files.append(f['name'])
    
    print(f"[Prefetch] Starting thumbnail generation for {len(all_files)} files...")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def process_file(filename):
        try:
            ext = os.path.splitext(filename)[1].lower()
            is_video = ext in ('.mp4', '.mov', '.livp')
            
            # 生成小缩略图 (200x200)
            cache_key = f"{filename}_200x200"
            cache_file = CACHE_DIR / "thumbs" / f"{quote(cache_key, safe='')}.jpg"
            if not cache_file.exists():
                print(f"[Prefetch] Generating thumb_200 for: {filename}")
                _generate_thumbnail_internal(filename, (200, 200), is_video, ext, cache_file, "200x200")
            else:
                print(f"[Prefetch] thumb_200 already exists: {filename}")
            
            # 生成中等预览图 (800x800)
            cache_key_large = f"{filename}_800x800"
            cache_file_large = CACHE_DIR / "thumbs" / f"{quote(cache_key_large, safe='')}.jpg"
            if not cache_file_large.exists():
                print(f"[Prefetch] Generating thumb_800 for: {filename}")
                _generate_thumbnail_internal(filename, (800, 800), is_video, ext, cache_file_large, "800x800")
            else:
                print(f"[Prefetch] thumb_800 already exists: {filename}")
            
            return True
        except Exception as e:
            print(f"[Prefetch] ✗ Error processing {filename}: {e}")
            return False
    
    processed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, fn): fn for fn in all_files}
        for future in as_completed(futures):
            filename = futures[future]
            try:
                if future.result():
                    processed += 1
                    print(f"[Prefetch] ✓ Completed {processed}/{len(all_files)}: {filename}")
            except Exception as e:
                print(f"[Prefetch] ✗ Exception for {filename}: {e}")
    
    print(f"[Prefetch] Completed! Processed {processed}/{len(all_files)} files.")
