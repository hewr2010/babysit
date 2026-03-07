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

import io
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

import requests
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener

# 注册 HEIF/HEIC 支持
register_heif_opener()

# 导入项目配置和数据库模块
from .config import CACHE_DIR, BAIDU_REMOTE_PATH, PCS_API_BASE, DATA_DIR
from .db import get_standalone_db, update_media_file, delete_media_file

# 刷新间隔（秒）
REFRESH_INTERVAL = 3 * 60  # 3分钟

# 支持的文件扩展名
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.livp')
VIDEO_EXTS = ('.mp4', '.mov', '.livp')


def get_access_token():
    """从 bypy 配置读取 token"""
    token_file = Path.home() / ".bypy" / "bypy.json"
    if not token_file.exists():
        return None
    with open(token_file) as f:
        import json
        return json.load(f).get('access_token')


def run_bypy(cmd, timeout=60):
    """运行 bypy 命令"""
    return subprocess.run(
        f"bypy {cmd}", shell=True, capture_output=True, text=True, timeout=timeout
    )


def extract_datetime_from_filename(filename):
    """从文件名提取拍摄日期和时间，返回(date_str, time_str)"""
    import re
    
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
                        'size': int(size),
                        'date': date_str,
                        'time': time_from_name or '',
                        'md5': md5,
                        'baidu_date': baidu_date_str
                    })
    return files


def get_download_url(filename):
    """获取百度网盘下载直链"""
    token = get_access_token()
    if not token:
        return None, "未授权"
    
    path = f'/apps/bypy{BAIDU_REMOTE_PATH}/{filename}'
    
    try:
        # 方法1: PCS API download 接口
        download_url = f"{PCS_API_BASE}?method=download&access_token={token}&path={quote(path, safe='')}"
        resp = requests.get(download_url, allow_redirects=False, timeout=10)
        
        if resp.status_code == 302:
            location = resp.headers.get('Location')
            if location:
                return location, None
        
        # 方法2: xpan 接口
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


def generate_image_thumbnail(img, size):
    """生成图片缩略图"""
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail(size, Image.Resampling.LANCZOS)
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    output.seek(0)
    return output


def generate_video_thumbnail(video_data, filename, size):
    """生成视频缩略图（提取第一帧）"""
    temp_dir = CACHE_DIR / "temp_video"
    temp_dir.mkdir(exist_ok=True)
    
    # 处理 .livp 文件
    if filename.lower().endswith('.livp'):
        try:
            with zipfile.ZipFile(io.BytesIO(video_data), 'r') as z:
                mov_name = None
                for name in z.namelist():
                    if name.lower().endswith('.mov'):
                        mov_name = name
                        break
                
                if not mov_name:
                    return None
                
                video_path = temp_dir / f"{filename}.mov"
                with open(video_path, 'wb') as f:
                    f.write(z.read(mov_name))
        except zipfile.BadZipFile:
            return None
    else:
        video_path = temp_dir / filename
        with open(video_path, 'wb') as f:
            f.write(video_data)
    
    # 使用 ffmpeg 提取第一帧
    temp_frame = temp_dir / f"{filename}_frame.jpg"
    try:
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
        
        return generate_image_thumbnail(img, size)
    except Exception as e:
        print(f"Error generating video thumbnail: {e}")
        video_path.unlink(missing_ok=True)
        temp_frame.unlink(missing_ok=True)
        return None


def extract_livp_video(video_data, filename):
    """从 .livp 文件中提取视频"""
    try:
        with zipfile.ZipFile(io.BytesIO(video_data), 'r') as z:
            mov_name = None
            for name in z.namelist():
                if name.lower().endswith('.mov'):
                    mov_name = name
                    break
            
            if not mov_name:
                return None
            
            return z.read(mov_name)
    except Exception as e:
        print(f"Error extracting video from {filename}: {e}")
        return None


def process_media_file(file_info, thumbs_dir, previews_dir, videos_dir):
    """
    处理单个媒体文件
    返回 (success, updated_info) 元组
    """
    filename = file_info['name']
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in VIDEO_EXTS
    
    print(f"  处理: {filename}")
    
    # 获取下载链接
    url, error = get_download_url(filename)
    if error or not url:
        print(f"    ❌ 无法获取下载链接: {error}")
        return False, file_info
    
    try:
        # 下载文件
        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            print(f"    ❌ 下载失败: HTTP {resp.status_code}")
            return False, file_info
        
        file_data = resp.content
        
        # 生成缩略图 (200x200)
        thumb_path = thumbs_dir / f"{quote(filename, safe='')}_200x200.jpg"
        if is_video:
            thumb_data = generate_video_thumbnail(file_data, filename, (200, 200))
        else:
            img = Image.open(io.BytesIO(file_data))
            # 提取 EXIF 时间
            exif_date, exif_time = extract_exif_datetime(img)
            if exif_date and exif_date != '0000-00-00':
                file_info['date'] = exif_date
                file_info['time'] = exif_time or file_info.get('time', '')
            thumb_data = generate_image_thumbnail(img, (200, 200))
        
        if thumb_data:
            with open(thumb_path, 'wb') as f:
                f.write(thumb_data.getvalue())
            print(f"    ✓ 缩略图已生成")
        else:
            print(f"    ❌ 缩略图生成失败")
            return False, file_info
        
        # 生成预览图 (800x800)
        preview_path = previews_dir / f"{quote(filename, safe='')}_800x800.jpg"
        if is_video:
            preview_data = generate_video_thumbnail(file_data, filename, (800, 800))
        else:
            img = Image.open(io.BytesIO(file_data))
            preview_data = generate_image_thumbnail(img, (800, 800))
        
        if preview_data:
            with open(preview_path, 'wb') as f:
                f.write(preview_data.getvalue())
            print(f"    ✓ 预览图已生成")
        else:
            print(f"    ❌ 预览图生成失败")
            return False, file_info
        
        # 如果是 .livp 文件，提取视频
        if ext == '.livp':
            video_data = extract_livp_video(file_data, filename)
            if video_data:
                video_path = videos_dir / f"{quote(filename, safe='')}.mov"
                with open(video_path, 'wb') as f:
                    f.write(video_data)
                print(f"    ✓ 视频已提取")
            else:
                print(f"    ❌ 视频提取失败")
                return False, file_info
        
        file_info['processed'] = True
        file_info['processed_at'] = datetime.now().isoformat()
        print(f"    ✓ 处理完成")
        return True, file_info
        
    except Exception as e:
        print(f"    ❌ 处理异常: {e}")
        return False, file_info


def refresh_media():
    """执行一次媒体刷新操作"""
    print(f"\n{'='*60}")
    print(f"🔄 开始媒体刷新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
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
        ext = os.path.splitext(f['name'])[1].lower()
        if ext in SUPPORTED_EXTS:
            f['type'] = 'video' if ext in VIDEO_EXTS else 'photo'
            f['processed'] = False
            media_files.append(f)
    
    print(f"📊 找到 {len(media_files)} 个多媒体文件")
    
    # 获取数据库连接
    db = get_standalone_db()
    
    try:
        # 处理每个文件
        new_count = 0
        updated_count = 0
        failed_count = 0
        current_names = set()
        
        for file_info in media_files:
            filename = file_info['name']
            md5 = file_info.get('md5', '')
            current_names.add(filename)
            
            # 检查数据库中是否已存在且未改变
            cursor = db.execute(
                "SELECT md5, processed FROM media_files WHERE filename = ?",
                (filename,)
            )
            existing = cursor.fetchone()
            
            if existing and existing['md5'] == md5 and existing['processed']:
                # 文件未改变且已处理，跳过
                continue
            
            # 需要处理这个文件
            success, updated_info = process_media_file(
                file_info, thumbs_dir, previews_dir, videos_dir
            )
            
            if success:
                # 更新数据库（使用事务）
                update_media_file(db, updated_info)
                db.commit()
                
                if existing is None:
                    new_count += 1
                else:
                    updated_count += 1
            else:
                failed_count += 1
                # 如果处理失败，不更新记录（保留旧的已处理记录）
        
        # 清理不存在的文件记录
        cursor = db.execute("SELECT filename FROM media_files")
        db_names = {row['filename'] for row in cursor.fetchall()}
        removed = db_names - current_names
        
        for name in removed:
            delete_media_file(db, name)
        
        if removed:
            db.commit()
            print(f"\n🗑️  清理了 {len(removed)} 个不存在的文件记录")
        
        # 统计
        cursor = db.execute(
            "SELECT COUNT(*) FROM media_files WHERE processed = 1"
        )
        total_available = cursor.fetchone()[0]
        
    finally:
        db.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 刷新完成")
    print(f"   新增: {new_count}")
    print(f"   更新: {updated_count}")
    print(f"   失败: {failed_count}")
    print(f"   总计可用: {total_available}")
    print(f"{'='*60}\n")


def main():
    """主循环"""
    print("\n" + "="*60)
    print("🚀 媒体刷新服务启动")
    print(f"⏱️  刷新间隔: {REFRESH_INTERVAL // 60} 分钟")
    print(f"🗄️  数据库: {DATA_DIR / 'babysit.db'}")
    print(f"☁️  网盘路径: {BAIDU_REMOTE_PATH}")
    print("="*60 + "\n")
    
    # 立即执行一次
    try:
        refresh_media()
    except Exception as e:
        print(f"❌ 首次刷新失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 定时循环
    while True:
        print(f"💤 等待 {REFRESH_INTERVAL // 60} 分钟后下次刷新...")
        time.sleep(REFRESH_INTERVAL)
        
        try:
            refresh_media()
        except Exception as e:
            print(f"❌ 刷新失败: {e}")
            import traceback
            traceback.print_exc()
            print("   将在下次循环重试...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
        sys.exit(0)
