"""百度网盘模块"""
import json
import subprocess
import io
import os
from pathlib import Path
from urllib.parse import quote, unquote
import requests
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
from .config import CACHE_DIR, BAIDU_REMOTE_PATH, PCS_API_BASE

# 注册 HEIF/HEIC 支持
register_heif_opener()

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

def get_file_info(filename):
    """获取百度网盘上指定文件的详细信息"""
    result = run_bypy(f"list '{BAIDU_REMOTE_PATH}'")
    if result.returncode != 0:
        return None
    
    files = parse_bypy_list(result.stdout)
    for f in files:
        if f['name'] == filename:
            return f
    return None

def extract_datetime_from_filename(filename):
    """从文件名提取拍摄日期和时间，返回(date_str, time_str)"""
    import re
    from datetime import datetime
    
    # 2026-03-01 101239.livp -> 2026-03-01, 10:12
    # 2026-02-27 144748.livp -> 2026-02-27, 14:47
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
    
    # P1010141.JPG 等相机格式，用网盘日期
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
        
        # 查找 DateTimeOriginal (36867) 或 DateTime (306)
        for tag_id, value in exif.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name in ('DateTimeOriginal', 'DateTime'):
                # 格式: '2026:02:12 14:30:45'
                if isinstance(value, str) and len(value) >= 19:
                    date_part = value[:10].replace(':', '-')  # '2026-02-12'
                    time_part = value[11:16]  # '14:30'
                    # 检查日期是否有效
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
            # bypy list 格式: F <filename> <size> <date>, <time> <md5>
            # 但是如果文件名中包含空格，会被分隔
            # 例: F 2026-02-27 144748.livp 8861291 2026-03-02, 11:52:53 hash
            parts = line.split(' ')
            if len(parts) >= 5:
                # parts[0] = 'F'
                # parts[1..n-3] = 文件名部分
                # parts[-3] = size
                # parts[-2] = date,
                # parts[-1] = time hash
                
                # 找到size字段（纯数字）
                size_idx = -1
                for i in range(1, len(parts)):
                    if parts[i].isdigit() and len(parts[i]) > 3:  # size通常很大
                        size_idx = i
                        break
                
                if size_idx > 1:
                    # 文件名是 parts[1] 到 parts[size_idx-1]
                    filename = ' '.join(parts[1:size_idx])
                    size = int(parts[size_idx])
                    # 网盘日期在 size 之后
                    baidu_date_str = parts[size_idx + 1].rstrip(',')
                    
                    # 从文件名提取日期
                    date_from_name, time_from_name = extract_datetime_from_filename(filename)
                    date_str = date_from_name if date_from_name else baidu_date_str
                    
                    # md5在最后
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
            # 更新EXIF时间
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
    
    # 按日期分组
    date_groups = {}
    for f in files:
        d = f['date']
        if d not in date_groups:
            date_groups[d] = []
        date_groups[d].append(f)
    
    # 每个日期内按时间排序（晚的在前）
    for d in date_groups:
        date_groups[d].sort(key=lambda x: x.get('time', ''), reverse=True)
    
    # 按日期排序（最新的在前）
    sorted_groups = dict(sorted(date_groups.items(), key=lambda x: x[0], reverse=True))
    
    with open(cache_file, 'w') as f:
        json.dump(sorted_groups, f)
    
    return update_files_with_exif(sorted_groups)

def update_files_with_exif(date_groups):
    """使EXIF缓存更新文件日期时间"""
    exif_cache = get_exif_cache()
    if not exif_cache:
        return date_groups
    
    # 重新构建按日期分组的结构
    new_groups = {}
    for date_str, files in date_groups.items():
        for f in files:
            filename = f['name']
            # 如果有EXIF时间缓存，优先使用
            if filename in exif_cache:
                f['date'] = exif_cache[filename]['date']
                f['time'] = exif_cache[filename]['time']
            
            d = f['date']
            if d not in new_groups:
                new_groups[d] = []
            new_groups[d].append(f)
    
    # 重新排序
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
        # 方法1: 先尝试 PCS API 的 download 接口
        download_url = f"{PCS_API_BASE}?method=download&access_token={token}&path={quote(path, safe='')}"
        resp = requests.get(download_url, allow_redirects=False, timeout=10)
        
        if resp.status_code == 302:
            location = resp.headers.get('Location')
            if location:
                return location, None
        
        # 方法2: 使用 xpan 接口获取 dlink
        # 首先需要获取文件的 fs_id
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
                # 使用 fs_id 获取 dlink
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
    
    # 尝试从缓存读取
    cache_key = f"{filename}_video"
    cache_file = CACHE_DIR / "livp_videos" / f"{quote(cache_key, safe='')}.mov"
    cache_file.parent.mkdir(exist_ok=True)
    
    if cache_file.exists():
        with open(cache_file, 'rb') as f:
            return io.BytesIO(f.read())
    
    # 下载 .livp 文件
    url, err = get_download_url(filename)
    if err or not url:
        return None
    
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            return None
        
        import zipfile
        # .livp 实际是 ZIP 文件，包含 HEIC 图片和 MOV 视频
        with zipfile.ZipFile(io.BytesIO(resp.content), 'r') as z:
            # 找到 MOV 文件
            mov_name = None
            for name in z.namelist():
                if name.lower().endswith('.mov'):
                    mov_name = name
                    break
            
            if not mov_name:
                return None
            
            # 读取 MOV 文件
            mov_data = z.read(mov_name)
            
            # 保存到缓存
            with open(cache_file, 'wb') as f:
                f.write(mov_data)
            
            return io.BytesIO(mov_data)
    except Exception as e:
        print(f"Error extracting video from {filename}: {e}")
        return None

def get_thumbnail_data(filename, size=(200, 200)):
    """获取缩略图数据（图片或视频封面）"""
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in ('.mp4', '.mov', '.livp')
    
    # 尝试从缓存读取
    cache_key = f"{filename}_{size[0]}x{size[1]}"
    cache_file = CACHE_DIR / "thumbs" / f"{quote(cache_key, safe='')}.jpg"
    cache_file.parent.mkdir(exist_ok=True)
    
    if cache_file.exists():
        with open(cache_file, 'rb') as f:
            return io.BytesIO(f.read())
    
    # 下载原图
    url, err = get_download_url(filename)
    if err or not url:
        return None
    
    try:
        if is_video:
            # 视频：使用ffmpeg提取第一帧
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                return None
            
            temp_video = CACHE_DIR / "temp_video"
            temp_video.mkdir(exist_ok=True)
            
            # 处理 .livp 文件（Live Photo，实际是 ZIP 包含 HEIC 和 MOV）
            if ext == '.livp':
                import zipfile
                try:
                    with zipfile.ZipFile(io.BytesIO(resp.content), 'r') as z:
                        # 找到 MOV 文件
                        mov_name = None
                        for name in z.namelist():
                            if name.lower().endswith('.mov'):
                                mov_name = name
                                break
                        
                        if not mov_name:
                            return None
                        
                        # 解压 MOV 文件
                        video_path = temp_video / f"{filename}.mov"
                        with open(video_path, 'wb') as f:
                            f.write(z.read(mov_name))
                except zipfile.BadZipFile:
                    return None
            else:
                # 普通视频文件
                video_path = temp_video / filename
                with open(video_path, 'wb') as f:
                    f.write(resp.content)
            
            # 使用ffmpeg提取第一帧
            temp_frame = temp_video / f"{filename}_frame.jpg"
            result = subprocess.run(
                ['ffmpeg', '-i', str(video_path), '-vframes', '1', '-q:v', '2', str(temp_frame)],
                capture_output=True,
                timeout=30
            )
            
            # 删除视频文件
            video_path.unlink(missing_ok=True)
            
            if result.returncode != 0 or not temp_frame.exists():
                return None
            
            # 读取并压缩帧
            img = Image.open(temp_frame)
            temp_frame.unlink(missing_ok=True)
        else:
            # 图片：下载并读取EXIF
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return None
                
            img = Image.open(io.BytesIO(resp.content))
            
            # 读取EXIF并缓存时间（只在首次生成缩略图时）
            if size == (200, 200):  # 只在生成小缩略图时检查EXIF
                date_str, time_str = extract_exif_datetime(img)
                # 如果EXIF中没有有效时间，使用网盘修改时间
                if not date_str or date_str == '0000-00-00':
                    # 从缓存的文件列表中查找该文件的网盘时间
                    cache_file_path = CACHE_DIR / "baidu_files.json"
                    if cache_file_path.exists():
                        import json
                        with open(cache_file_path) as f:
                            all_files = json.load(f)
                            for date, file_list in all_files.items():
                                for f_info in file_list:
                                    if f_info['name'] == filename:
                                        # 使用 baidu_date 作为回退
                                        date_str = f_info.get('baidu_date') or f_info.get('date', '')
                                        time_str = ''
                                        break
                                if date_str:
                                    break
                
                if date_str:
                    exif_cache = get_exif_cache()
                    exif_cache[filename] = {'date': date_str, 'time': time_str or ''}
                    save_exif_cache(exif_cache)
        
        # 统一处理图片
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        # 保存到缓存
        with open(cache_file, 'wb') as f:
            f.write(output.getvalue())
        output.seek(0)
        return output
    except Exception as e:
        print(f"Error generating thumbnail for {filename}: {e}")
        return None
