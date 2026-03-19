"""
babysit - 宝宝成长管家 (Vue3版)

使用方法:
    python -m babysit.app
"""

import io
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, quote

from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, redirect, Response
from PIL import Image

from .config import DATA_DIR, CACHE_DIR
from .db import (init_db, close_db, get_baby, add_baby, 
                 get_growth_records, add_growth, delete_growth,
                 get_all_processed_media, get_processed_media_by_month)
from .utils import calculate_age
from .baidu import get_file_info, run_bypy

# Vue3 frontend dist directory
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


def create_app():
    # Check if Vue3 dist exists, fallback to templates if not
    if FRONTEND_DIST.exists():
        app = Flask(__name__, static_folder=str(FRONTEND_DIST / "assets"), static_url_path="/assets")
    else:
        app = Flask(__name__, template_folder=str(DATA_DIR.parent / "templates"))
    
    app.teardown_appcontext(close_db)
    init_db()
    
    @app.route("/")
    def index():
        if FRONTEND_DIST.exists():
            return send_from_directory(FRONTEND_DIST, "index.html")
        return render_template("index.html")
    
    @app.route("/<int:year>/<int:month>")
    def month_view(year, month):
        """Handle /<year>/<month> URLs"""
        if FRONTEND_DIST.exists():
            return send_from_directory(FRONTEND_DIST, "index.html")
        return render_template("index.html")
    
    @app.route("/<path:filename>")
    def static_files(filename):
        """Serve static files from Vue3 dist"""
        if FRONTEND_DIST.exists():
            # Check if file exists in dist
            file_path = FRONTEND_DIST / filename
            if file_path.exists() and file_path.is_file():
                # 为 txt 文件显式设置 mimetype，确保微信验证能正确识别
                if filename.endswith('.txt'):
                    return send_from_directory(FRONTEND_DIST, filename, mimetype='text/plain')
                return send_from_directory(FRONTEND_DIST, filename)
        return jsonify({"error": "Not found"}), 404
    
    # ===== 宝宝信息 =====
    @app.route("/api/baby", methods=["GET", "POST"])
    def api_baby():
        if request.method == "POST":
            add_baby(request.json)
            return jsonify({"message": "保存成功"})
        return jsonify(get_baby() or {})
    
    # ===== 成长记录 =====
    @app.route("/api/growth", methods=["GET", "POST"])
    def api_growth():
        """成长记录"""
        if request.method == "POST":
            add_growth(request.json)
            return jsonify({"message": "保存成功"})
        return jsonify(get_growth_records())
    
    @app.route("/api/growth/<int:id>", methods=["DELETE"])
    def api_delete_growth(id):
        """删除成长记录"""
        delete_growth(id)
        return jsonify({"message": "删除成功"})
    
    # ===== 相册 =====
    @app.route("/api/album")
    def api_album():
        """获取所有已预处理的媒体文件，按月分组"""
        return jsonify(get_all_processed_media())
    
    @app.route("/api/album/<int:year>/<int:month>")
    def api_album_month(year, month):
        """获取某月已预处理的媒体文件"""
        return jsonify(get_processed_media_by_month(year, month))
    
    # ===== 缩略图（从缓存读取，已预生成）=====
    @app.route("/thumb/<path:filename>")
    def thumbnail(filename):
        """获取缩略图 (200x200) - 从缓存读取"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        cache_key = f"{quote(filename, safe='')}_200x200.jpg"
        cache_file = CACHE_DIR / "thumbs" / cache_key
        
        if cache_file.exists():
            return send_file(cache_file, mimetype='image/jpeg')
        
        # 如果缓存不存在，返回占位图
        placeholder = io.BytesIO()
        Image.new('RGB', (200, 200), color='#ffc0cb').save(placeholder, format='JPEG')
        placeholder.seek(0)
        return send_file(placeholder, mimetype='image/jpeg')
    
    @app.route("/preview/<path:filename>")
    def preview(filename):
        """获取中等质量预览图 (800x800) - 从缓存读取"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        cache_key = f"{quote(filename, safe='')}_800x800.jpg"
        cache_file = CACHE_DIR / "previews" / cache_key
        
        if cache_file.exists():
            return send_file(cache_file, mimetype='image/jpeg')
        
        # 如果缓存不存在，返回占位图
        placeholder = io.BytesIO()
        Image.new('RGB', (400, 400), color='#ffc0cb').save(placeholder, format='JPEG')
        placeholder.seek(0)
        return send_file(placeholder, mimetype='image/jpeg')
    
    @app.route("/livp/<path:filename>")
    def livp_video(filename):
        """从已预提取的 .livp 视频中获取"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        cache_key = f"{quote(filename, safe='')}.mov"
        cache_file = CACHE_DIR / "videos" / cache_key
        
        if cache_file.exists():
            return send_file(cache_file, mimetype='video/quicktime')
        
        return jsonify({"error": "视频未预处理完成"}), 404
    
    @app.route("/video/<path:filename>")
    def video_proxy(filename):
        """获取视频文件（从本地缓存，避免 CORS 问题）"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        # 验证文件类型
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.mov', '.mp4'):
            return jsonify({"error": "不支持的视频格式"}), 400
        
        # 首先尝试从本地缓存读取
        cache_key = quote(filename, safe='')
        cache_file = CACHE_DIR / "videos" / cache_key
        
        if cache_file.exists():
            mimetype = 'video/quicktime' if ext == '.mov' else 'video/mp4'
            return send_file(cache_file, mimetype=mimetype)
        
        # 缓存不存在，返回 404（让 refresh_media 去下载）
        return jsonify({"error": "视频未缓存，请等待后台处理"}), 404
    
    # ===== 原文件下载（服务器流式代理，不落盘）=====
    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    
    @app.route("/api/download/<path:filename>")
    def download_original(filename):
        """流式下载原文件 - 服务器代理，不缓存到磁盘（限制 50MB）"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        # 验证文件类型
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.livp'):
            return jsonify({"error": "不支持的文件格式"}), 400
        
        # 获取文件信息（检查大小）
        file_info = get_file_info(filename)
        if not file_info:
            return jsonify({"error": "无法获取文件信息"}), 404
        
        file_size = file_info.get('size', 0)
        if file_size > MAX_DOWNLOAD_SIZE:
            return jsonify({
                "error": "文件过大",
                "message": f"文件大小 {format_file_size(file_size)} 超过 50MB 限制，无法下载",
                "size": file_size,
                "size_formatted": format_file_size(file_size)
            }), 413
        
        # livp 文件特殊处理：提取 mov 视频
        if ext == '.livp':
            return download_livp_video(filename, file_size)
        
        # 普通文件：流式代理
        return stream_proxy_download(filename, file_size)
    
    def download_livp_video(filename, file_size):
        """从 livp 中提取 mov 视频并流式返回"""
        from .baidu import get_download_url
        import requests
        import zipfile
        
        download_url, error = get_download_url(filename)
        if error or not download_url:
            return jsonify({"error": "无法获取下载链接", "details": error}), 500
        
        temp_livp_path = None
        
        try:
            # 流式下载 livp 到临时文件（避免内存溢出）
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.livp') as temp_livp:
                temp_livp_path = temp_livp.name
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
                
                with requests.get(download_url, stream=True, headers=headers, timeout=120) as resp:
                    if resp.status_code != 200:
                        return jsonify({"error": f"下载失败: {resp.status_code}"}), 500
                    
                    # 流式写入临时文件
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            temp_livp.write(chunk)
            
            # 打开 zip 文件并保持引用
            z = zipfile.ZipFile(temp_livp_path, 'r')
            
            # 找到 mov 文件
            mov_name = None
            for name in z.namelist():
                if name.lower().endswith('.mov'):
                    mov_name = name
                    break
            
            if not mov_name:
                z.close()
                os.unlink(temp_livp_path)
                return jsonify({"error": "livp 中未找到视频"}), 500
            
            # 获取 mov 文件信息
            mov_info = z.getinfo(mov_name)
            mov_size = mov_info.file_size
            
            # 构造下载文件名
            download_name = filename.replace('.livp', '.mov')
            
            # 流式返回 mov 文件 - 使用闭包保持文件引用
            mov_file = z.open(mov_name)
            
            def generate_mov():
                try:
                    while True:
                        chunk = mov_file.read(65536)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    # 清理资源
                    try:
                        mov_file.close()
                    except:
                        pass
                    try:
                        z.close()
                    except:
                        pass
                    try:
                        if temp_livp_path:
                            os.unlink(temp_livp_path)
                    except:
                        pass
            
            return Response(
                generate_mov(),
                mimetype='video/quicktime',
                headers={
                    'Content-Disposition': f'attachment; filename="{download_name}"',
                    'Content-Length': str(mov_size)
                }
            )
                
        except Exception as e:
            # 清理资源
            try:
                if temp_livp_path:
                    os.unlink(temp_livp_path)
            except:
                pass
            return jsonify({"error": f"提取视频失败: {str(e)}"}), 500
    
    def stream_proxy_download(filename, file_size):
        """普通文件的流式代理下载"""
        from .baidu import get_download_url
        import requests
        
        download_url, error = get_download_url(filename)
        if error or not download_url:
            return jsonify({"error": "无法获取下载链接", "details": error}), 500
        
        mimetype = get_mimetype(filename)
        
        def generate():
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                }
                
                with requests.get(download_url, stream=True, headers=headers, timeout=60) as resp:
                    if resp.status_code != 200:
                        print(f"Baidu download error: {resp.status_code}")
                        return
                    
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            yield chunk
                            
            except Exception as e:
                print(f"Stream proxy error: {e}")
                raise
        
        return Response(
            generate(),
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(file_size)
            }
        )
    
    def get_mimetype(filename):
        """根据文件名获取 MIME 类型"""
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.heic': 'image/heic',
            '.livp': 'application/octet-stream'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def format_file_size(size):
        """格式化文件大小"""
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f}GB"
    
    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
