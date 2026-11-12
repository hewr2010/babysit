"""
babysit - 宝宝成长管家 (Vue3版)

使用方法:
    python -m babysit.app
"""

import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, quote

from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, redirect, Response

from .config import DATA_DIR, CACHE_DIR
from .db import (init_db, close_db, get_baby, add_baby,
                 get_growth_records, add_growth, delete_growth,
                 get_all_processed_media, get_processed_media_by_month,
                 get_all_milestones, get_milestones_by_filename, add_milestone, delete_milestone)
from .utils import calculate_age
from .baidu import get_file_info, run_bypy
from .media_cache import (
    enqueue_original_livp,
    enqueue_warm,
    existing_video_path,
    get_media_status,
    get_original_livp_status,
    init_media_cache,
    original_livp_path,
    partial_video_path,
    touch_media_access,
)

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
    init_media_cache()

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

    # ===== 重要时刻 =====
    @app.route("/api/milestones", methods=["GET", "POST"])
    def api_milestones():
        """获取所有重要时刻或创建新时刻"""
        if request.method == "POST":
            data = request.json
            if not data.get('media_filename') or not data.get('title'):
                return jsonify({"error": "media_filename 和 title 是必填项"}), 400
            add_milestone(data)
            return jsonify({"message": "标记成功"})
        return jsonify(get_all_milestones())

    @app.route("/api/milestones/<path:filename>", methods=["GET"])
    def api_milestones_by_filename(filename):
        """获取某张照片关联的所有重要时刻"""
        try:
            filename = unquote(filename)
        except:
            pass
        return jsonify(get_milestones_by_filename(filename))

    @app.route("/api/milestones/<int:id>", methods=["DELETE"])
    def api_delete_milestone(id):
        """删除重要时刻"""
        delete_milestone(id)
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

    @app.route("/api/media/status/<path:filename>")
    def api_media_status(filename):
        return jsonify(get_media_status(filename))

    @app.route("/api/media/warm", methods=["POST"])
    def api_media_warm():
        data = request.get_json(silent=True) or {}
        filename = data.get("filename", "")
        neighbors = data.get("neighbors", [])
        client_id = data.get("client_id", "")[:80]
        if not filename or not client_id:
            return jsonify({"error": "filename 和 client_id 是必填项"}), 400
        if not isinstance(neighbors, list) or len(neighbors) > 4:
            return jsonify({"error": "neighbors 最多包含 4 个文件"}), 400
        from .db import get_db

        names = [filename, *neighbors]
        placeholders = ",".join("?" for _ in names)
        rows = get_db().execute(
            f"SELECT filename FROM media_files WHERE processed = 1 "
            f"AND filename IN ({placeholders})",
            names,
        ).fetchall()
        known_names = {row["filename"] for row in rows}
        if filename not in known_names:
            return jsonify({"error": "媒体不存在或尚未完成首次处理"}), 404
        neighbors = [name for name in neighbors if name in known_names]
        status = enqueue_warm(
            filename,
            client_id,
            neighbors,
            generation=max(0, int(data.get("generation", 0))),
            include_current=bool(data.get("include_current", True)),
            include_neighbor_videos=bool(data.get("include_neighbor_videos", False)),
        )
        return jsonify({"current": status, "neighbors": neighbors}), (
            200 if status["state"] == "ready" else 202
        )

    @app.route("/thumb/<path:filename>")
    def thumbnail(filename):
        cache_file = CACHE_DIR / "thumbs" / f"{quote(filename, safe='')}_200x200.jpg"
        if not cache_file.exists():
            try:
                recover_cold_media(filename)
            except (TimeoutError, RuntimeError) as error:
                return jsonify({"error": "RECOVERY_FAILED", "message": str(error)}), 503
            except FileNotFoundError:
                return jsonify({"error": "媒体不存在"}), 404
        if cache_file.exists():
            return send_file(cache_file, mimetype="image/jpeg")
        return jsonify({"error": "RECOVERY_FAILED", "message": "缩略图恢复失败"}), 503

    def recover_cold_media(filename):
        from .db import get_db

        rows = get_db().execute(
            "SELECT filename FROM media_files WHERE processed = 1 "
            "ORDER BY date DESC, time DESC"
        ).fetchall()
        names = [row["filename"] for row in rows]
        if filename not in names:
            raise FileNotFoundError(filename)
        index = names.index(filename)
        neighbor_indexes = [index - 2, index - 1, index + 1, index + 2]
        neighbors = [names[i] for i in neighbor_indexes if 0 <= i < len(names)]
        enqueue_warm(
            filename,
            "native-preview",
            neighbors,
            generation=time.time_ns(),
            include_neighbor_videos=True,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            status = get_media_status(filename)
            if status["state"] in ("ready", "streaming"):
                return status
            if status["state"] == "error":
                raise RuntimeError((status.get("job") or {}).get("error") or "媒体恢复失败")
            time.sleep(0.1)
        raise TimeoutError("媒体恢复超时，请重试")

    @app.route("/preview/<path:filename>")
    def preview(filename):
        cache_file = CACHE_DIR / "previews" / f"{quote(filename, safe='')}_800x800.jpg"
        if not cache_file.exists():
            try:
                recover_cold_media(filename)
            except (TimeoutError, RuntimeError) as error:
                return jsonify({"error": "RECOVERY_FAILED", "message": str(error)}), 503
            except FileNotFoundError:
                return jsonify({"error": "媒体不存在"}), 404
        if cache_file.exists():
            touch_media_access(filename, "preview")
            return send_file(cache_file, mimetype="image/jpeg")
        return jsonify({"error": "RECOVERY_FAILED", "message": "预览恢复失败"}), 503

    def serve_cached_video(filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".mov", ".mp4", ".livp"):
            return jsonify({"error": "不支持的视频格式"}), 400
        cache_file = existing_video_path(filename)
        if not cache_file:
            try:
                recover_cold_media(filename)
            except (TimeoutError, RuntimeError) as error:
                return jsonify({"error": "RECOVERY_FAILED", "message": str(error)}), 503
            except FileNotFoundError:
                return jsonify({"error": "媒体不存在"}), 404
            cache_file = existing_video_path(filename)
        if not cache_file and get_media_status(filename)["state"] == "streaming":
            cache_file = partial_video_path(filename)
        if not cache_file:
            return jsonify({"error": "RECOVERY_FAILED", "message": "视频恢复失败"}), 503
        touch_media_access(filename, "video")
        mimetype = "video/mp4" if cache_file.suffix.lower() == ".mp4" else "video/quicktime"
        return send_file(cache_file, mimetype=mimetype, conditional=True)

    @app.route("/livp/<path:filename>")
    def livp_video(filename):
        return serve_cached_video(filename)

    @app.route("/video/<path:filename>")
    def video_proxy(filename):
        return serve_cached_video(filename)

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
        enqueue_original_livp(filename)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            status = get_original_livp_status(filename)
            if status["state"] == "error":
                return jsonify({"error": "Live Photo 原件解包失败"}), 503
            if status["state"] == "ready":
                break
            time.sleep(0.1)
        original = original_livp_path(filename)
        if not original.exists():
            return jsonify({"error": "Live Photo 原件准备超时，请重试"}), 503
        response = send_file(
            original,
            mimetype="video/quicktime",
            as_attachment=True,
            download_name=filename.replace(".livp", ".mov"),
            conditional=True,
        )
        response.call_on_close(lambda: original.unlink(missing_ok=True))
        return response

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
