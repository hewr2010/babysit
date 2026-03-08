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

from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, redirect
from PIL import Image

from .config import DATA_DIR, CACHE_DIR
from .db import (init_db, close_db, get_baby, add_baby, 
                 get_growth_records, add_growth, delete_growth,
                 get_all_processed_media, get_processed_media_by_month)
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
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
