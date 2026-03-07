"""
babysit - 宝宝成长管家 (Vue3版)

使用方法:
    python -m babysit.app
"""

import io
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, render_template, jsonify, request, send_file, send_from_directory
from PIL import Image

from .config import DATA_DIR
from .db import init_db, close_db, get_baby, add_baby, get_growth_records, add_growth, delete_growth
from .baidu import (get_baidu_files, get_download_url, get_thumbnail_data, 
                    extract_livp_video, prefetch_thumbnails, get_processing_status,
                    register_sse_client, unregister_sse_client)
from .utils import calculate_age

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
    
    @app.route("/download/<path:filename>")
    def download_file(filename):
        """代理下载文件（避免浏览器直接访问百度PCS被拒绝）"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        # 获取百度PCS下载URL
        url, error = get_download_url(filename)
        if error:
            return f"获取下载链接失败: {error}", 500
        
        # 代理下载
        import requests
        from flask import Response
        try:
            resp = requests.get(url, stream=True, timeout=30)
            if resp.status_code != 200:
                return f"下载失败: HTTP {resp.status_code}", resp.status_code
            
            # 获取文件类型
            content_type = resp.headers.get('content-type', 'application/octet-stream')
            
            # 流式返回文件
            return Response(
                resp.iter_content(chunk_size=8192),
                content_type=content_type,
                headers={
                    'Content-Disposition': f'inline; filename="{filename}"',
                    'Content-Length': resp.headers.get('content-length', '')
                }
            )
        except Exception as e:
            return f"下载失败: {str(e)}", 500
    
    @app.route("/<path:filename>")
    def static_files(filename):
        """Serve static files from Vue3 dist"""
        if FRONTEND_DIST.exists():
            # Check if file exists in dist
            file_path = FRONTEND_DIST / filename
            if file_path.exists() and file_path.is_file():
                return send_from_directory(FRONTEND_DIST, filename)
        return jsonify({"error": "Not found"}), 404
    
    # ===== 宝宝信息 =====
    @app.route("/api/baby", methods=["GET", "POST"])
    def api_baby():
        if request.method == "POST":
            add_baby(request.json)
            return jsonify({"message": "保存成功"})
        return jsonify(get_baby() or {})
    
    # ===== 生长记录 =====
    @app.route("/api/growth", methods=["GET", "POST"])
    def api_growth():
        """生长记录"""
        if request.method == "POST":
            add_growth(request.json)
            return jsonify({"message": "保存成功"})
        return jsonify(get_growth_records())
    
    @app.route("/api/growth/<int:id>", methods=["DELETE"])
    def api_delete_growth(id):
        """删除生长记录"""
        delete_growth(id)
        return jsonify({"message": "删除成功"})
    
    # ===== 相册 =====
    @app.route("/api/album")
    def api_album():
        """获取所有照片，按月分组"""
        return jsonify(get_baidu_files())
    
    @app.route("/api/album/refresh")
    def api_album_refresh():
        """刷新相册缓存（会重新应用EXIF时间）"""
        files = get_baidu_files(force_refresh=True)
        # 后台预生成缩略图，不阻塞响应
        prefetch_thumbnails_async(files)
        return jsonify({"count": sum(len(v) for v in files.values())})
    
    @app.route("/api/album/<int:year>/<int:month>")
    def api_album_month(year, month):
        """获取某月照片"""
        all_files = get_baidu_files()
        prefix = f"{year}-{month:02d}"
        result = {}
        for date_str, files in all_files.items():
            if date_str.startswith(prefix):
                result[date_str] = files
        return jsonify(result)
    
    @app.route("/api/media/status/<path:filename>")
    def api_media_status(filename):
        """获取媒体文件处理状态"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        status = get_processing_status(filename)
        return jsonify(status)
    
    @app.route("/api/media/events")
    def api_media_events():
        """SSE 端点：实时推送媒体处理状态更新"""
        from flask import Response, stream_with_context
        import queue
        
        @stream_with_context
        def event_stream():
            client_queue = register_sse_client()
            try:
                # 发送初始连接成功消息
                yield f"data: {json.dumps({'type': 'connected', 'time': time.time()})}\n\n"
                
                while True:
                    try:
                        # 等待消息，最多 30 秒（保持连接活跃）
                        message = client_queue.get(timeout=30)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # 发送心跳保持连接
                        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            except GeneratorExit:
                # 客户端断开连接
                pass
            finally:
                unregister_sse_client(client_queue)
        
        return Response(
            event_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲
            }
        )
    
    @app.route("/thumb/<path:filename>")
    def thumbnail(filename):
        """获取缩略图 (200x200)"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        thumb_data = get_thumbnail_data(filename, size=(200, 200))
        if thumb_data:
            return send_file(thumb_data, mimetype='image/jpeg')
        
        # 如果失败，返回占位图
        placeholder = io.BytesIO()
        Image.new('RGB', (200, 200), color='#ffc0cb').save(placeholder, format='JPEG')
        placeholder.seek(0)
        return send_file(placeholder, mimetype='image/jpeg')
    
    @app.route("/preview/<path:filename>")
    def preview(filename):
        """获取中等质量预览图 (800x800)"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        thumb_data = get_thumbnail_data(filename, size=(800, 800))
        if thumb_data:
            return send_file(thumb_data, mimetype='image/jpeg')
        
        # 如果失败，返回占位图
        placeholder = io.BytesIO()
        Image.new('RGB', (400, 400), color='#ffc0cb').save(placeholder, format='JPEG')
        placeholder.seek(0)
        return send_file(placeholder, mimetype='image/jpeg')
    
    @app.route("/api/url/<path:filename>")
    def api_url(filename):
        """获取原图/视频 URL"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        url, error = get_download_url(filename)
        if error:
            return jsonify({"error": error}), 500
        return jsonify({"url": url})
    
    @app.route("/livp/<path:filename>")
    def livp_video(filename):
        """从 .livp 文件中提取视频部分并返回"""
        try:
            filename = unquote(filename)
        except:
            pass
        
        video_data = extract_livp_video(filename)
        if video_data:
            return send_file(video_data, mimetype='video/quicktime')
        
        return jsonify({"error": "无法提取视频"}), 500
    
    return app


def prefetch_thumbnails_async(files_by_date):
    """后台异步预生成缩略图"""
    import threading
    
    def prefetch():
        try:
            prefetch_thumbnails(files_by_date)
        except Exception as e:
            print(f"Prefetch error: {e}")
    
    thread = threading.Thread(target=prefetch, daemon=True)
    thread.start()


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
