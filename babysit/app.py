"""
babysit - 基于百度网盘直链的轻量级相册

使用方法:
    python -m babysit.app
    或
    python babysit/app.py
"""

import os
import json
import subprocess
import re
import sys
import io
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

import requests
from flask import Flask, render_template, jsonify, redirect, send_file, make_response
from PIL import Image

from babysit.config import (
    BAIDU_REMOTE_PATH, CACHE_DIR, THUMBNAIL_DIR,
    PHOTO_EXTS, VIDEO_EXTS, ALL_MEDIA_EXTS
)

# 百度网盘 API 配置
PCS_API_BASE = "https://pcs.baidu.com/rest/2.0/pcs/file"

# 确保目录存在
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


def get_access_token():
    """从 bypy 配置读取 access token"""
    config_dir = os.path.expanduser("~/.bypy")
    token_file = os.path.join(config_dir, "bypy.json")
    
    if not os.path.exists(token_file):
        return None
    
    with open(token_file, 'r') as f:
        token_data = json.load(f)
        return token_data.get('access_token')


def run_bypy(cmd, timeout=60):
    """运行 bypy 命令"""
    full_cmd = f"bypy {cmd}"
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, 
        text=True, timeout=timeout
    )
    return result


def parse_bypy_list(output):
    """解析 bypy list 的输出"""
    files = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('[') or line.startswith('<E>'):
            continue
        if line.startswith('F '):
            parts = line.split(' ', 4)
            if len(parts) >= 4:
                filename = parts[1]
                size = parts[2]
                date_str = parts[3]
                md5 = parts[4] if len(parts) > 4 else ''
                files.append({
                    'name': filename,
                    'size': size,
                    'date': date_str,
                    'md5': md5
                })
    return files


def extract_date_from_filename(filename):
    """从文件名提取日期"""
    patterns = [
        r'IMG_(\d{4})(\d{2})(\d{2})_',
        r'VID_(\d{4})(\d{2})(\d{2})_',
        r'video_(\d{4})(\d{2})(\d{2})_',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            if len(match.groups()) >= 3:
                year, month, day = match.groups()[:3]
                return f"{year}-{month}-{day}"
    
    # 从 mmexport 时间戳转换
    mm_match = re.search(r'mmexport(\d{13})', filename)
    if mm_match:
        timestamp_ms = int(mm_match.group(1))
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d")
    
    return "未知日期"


def get_file_index(force_refresh=False):
    """获取文件索引（带缓存）"""
    index_file = os.path.join(CACHE_DIR, "file_index.json")
    
    if not force_refresh and os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    result = run_bypy(f"list '{BAIDU_REMOTE_PATH}'")
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return []
    
    files = parse_bypy_list(result.stdout)
    
    media_files = []
    for f in files:
        ext = os.path.splitext(f['name'])[1].lower()
        if ext in ALL_MEDIA_EXTS:
            f['ext'] = ext
            f['date'] = extract_date_from_filename(f['name'])
            f['type'] = 'video' if ext in VIDEO_EXTS else 'photo'
            media_files.append(f)
    
    media_files.sort(key=lambda x: (x['date'], x['name']), reverse=True)
    
    # 确保缓存目录存在
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(media_files, f, ensure_ascii=False, indent=2)
    
    return media_files


def get_files_by_date():
    """按日期分组"""
    files = get_file_index()
    date_groups = {}
    
    for f in files:
        date = f['date']
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(f)
    
    return dict(sorted(date_groups.items(), reverse=True))


def get_download_url(filename):
    """获取百度网盘文件的下载链接"""
    access_token = get_access_token()
    if not access_token:
        return None, "未找到 access token"
    
    # 完整的远程路径
    remote_path = f"/apps/bypy{BAIDU_REMOTE_PATH}/{filename}"
    encoded_path = quote(remote_path, safe='')
    
    # 调用 PCS API 获取下载链接
    url = f"{PCS_API_BASE}?method=download&access_token={access_token}&path={encoded_path}"
    
    try:
        response = requests.get(url, allow_redirects=False, timeout=10)
        
        if response.status_code == 302:
            download_url = response.headers.get('Location')
            if download_url:
                return download_url, None
            else:
                return None, "未获取到下载链接"
        elif response.status_code == 200:
            return None, "API 返回了内容而非重定向"
        else:
            return None, f"API 错误: {response.status_code}"
    except Exception as e:
        return None, str(e)


def generate_thumbnail(filename, size=(300, 300)):
    """生成缩略图，返回 BytesIO 对象"""
    ext = os.path.splitext(filename)[1].lower()
    
    # 视频返回 None，用占位图
    if ext in VIDEO_EXTS:
        return None
    
    # 检查缓存
    thumb_filename = quote(filename, safe='') + f"_{size[0]}x{size[1]}.jpg"
    thumb_path = os.path.join(THUMBNAIL_DIR, thumb_filename)
    
    if os.path.exists(thumb_path):
        with open(thumb_path, 'rb') as f:
            return io.BytesIO(f.read())
    
    # 获取原图 URL
    url, error = get_download_url(filename)
    if error or not url:
        return None
    
    # 下载并生成缩略图
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return None
        
        img = Image.open(io.BytesIO(response.content))
        
        # 转换为 RGB（处理 PNG 等带透明通道的图片）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 等比例缩放到指定尺寸
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # 保存到内存
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        # 保存到缓存
        with open(thumb_path, 'wb') as f:
            f.write(output.getvalue())
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"生成缩略图失败 {filename}: {e}")
        return None


def create_app():
    """创建 Flask 应用"""
    # 获取包目录路径
    package_dir = Path(__file__).parent
    template_dir = package_dir / "templates"
    
    app = Flask(__name__, template_folder=str(template_dir))
    
    @app.route("/")
    def index():
        """首页 - 按日期显示"""
        date_groups = get_files_by_date()
        return render_template("index.html", date_groups=date_groups)
    
    @app.route("/api/files")
    def api_files():
        """API: 获取文件列表"""
        date_groups = get_files_by_date()
        return jsonify(date_groups)
    
    @app.route("/api/refresh")
    def api_refresh():
        """API: 刷新文件索引"""
        files = get_file_index(force_refresh=True)
        return jsonify({"count": len(files), "message": "刷新成功"})
    
    @app.route("/api/url/<path:filename>")
    def api_get_url(filename):
        """API: 获取文件的下载 URL"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        download_url, error = get_download_url(filename)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({
            "url": download_url,
            "filename": filename
        })
    
    @app.route("/thumb/<path:filename>")
    def thumbnail(filename):
        """获取缩略图"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        thumb = generate_thumbnail(filename)
        
        if thumb:
            return send_file(thumb, mimetype='image/jpeg')
        else:
            # 视频或生成失败，返回占位图
            placeholder = io.BytesIO()
            img = Image.new('RGB', (300, 300), color='#667eea')
            img.save(placeholder, format='JPEG')
            placeholder.seek(0)
            return send_file(placeholder, mimetype='image/jpeg')
    
    @app.route("/view/<path:filename>")
    def view_file(filename):
        """查看/播放文件 - 重定向到百度网盘直链"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        download_url, error = get_download_url(filename)
        
        if error:
            return f"获取下载链接失败: {error}", 500
        
        return redirect(download_url, code=302)
    
    return app


if __name__ == "__main__":
    print("=" * 60)
    print("babysit - 基于百度网盘的轻量级相册")
    print("=" * 60)
    print(f"数据目录: {CACHE_DIR}")
    print(f"缩略图目录: {THUMBNAIL_DIR}")
    print(f"百度网盘路径: {BAIDU_REMOTE_PATH}")
    
    # 检查 token
    token = get_access_token()
    if not token:
        print("\n错误: 未找到 access token")
        print("请先运行: bypy info")
        sys.exit(1)
    
    print(f"Access Token: {token[:20]}...")
    
    # 预加载索引
    print("\n正在加载文件索引...")
    files = get_file_index()
    print(f"找到 {len(files)} 个媒体文件")
    
    # 测试获取一个文件的 URL
    if files:
        test_file = files[0]['name']
        url, err = get_download_url(test_file)
        if url:
            print(f"✓ 直链测试成功")
        else:
            print(f"✗ 直链测试失败: {err}")
    
    print("=" * 60)
    print("启动服务: http://localhost:8080")
    print("按 Ctrl+C 停止")
    print("=" * 60)
    
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
