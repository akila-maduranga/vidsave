import os
import asyncio
import urllib.parse
import uuid
import threading
import hashlib
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
from plugins.config import Config
import time

def humanbytes(size):
    """Convert bytes to human readable format."""
    if not size:
        return "0B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}PB"

# Serve the new web frontend
app = Flask(__name__, static_folder="web_new")

# Secret key for JWT
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'keepthisclip-secret-key-change-in-production')

# Runtime flags
app.is_ready = False
app.is_shutting_down = False

# Global cache for HTML
_INDEX_HTML_CACHE = None

# Import download progress tracking from upload.py
from plugins.helper.upload import WEB_DOWNLOAD_PROGRESS as DOWNLOAD_PROGRESS

# Admin credentials (default: admin/admin123)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Traffic tracking
TRAFFIC_STATS = {
    'total_downloads': 0,
    'data_transferred_bytes': 0,
    'recent_downloads': [],
    'daily_stats': {}
}

# Site configuration
SITE_CONFIG = {
    'site_name': 'KeepThisClip',
    'max_file_size_gb': 2,
    'download_timeout': 300
}

# Mark app as ready immediately (for gunicorn workers)
app.is_ready = True

async def prune_progress_task():
    """Background task to keep memory low by pruning old progress data."""
    while True:
        try:
            now = time.time()
            to_del = [did for did, info in DOWNLOAD_PROGRESS.items() 
                      if now - info.get("_last_update", now) > 3600]
            for did in to_del:
                # Clean up downloaded file before deleting entry
                filepath = DOWNLOAD_PROGRESS.get(did, {}).get("filepath")
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
                del DOWNLOAD_PROGRESS[did]
        except Exception:
            pass
        await asyncio.sleep(300)  # Check every 5 minutes

# ── Web Frontend Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main web interface."""
    global _INDEX_HTML_CACHE
    if _INDEX_HTML_CACHE is None:
        with open(os.path.join(app.static_folder, "index.html"), "r", encoding="utf-8") as f:
            _INDEX_HTML_CACHE = f.read()
    return _INDEX_HTML_CACHE

@app.route("/<path:path>")
def static_files(path):
    """Serve static files."""
    return send_from_directory(app.static_folder, path)

# ── API Endpoints ───────────────────────────────────────────────────────────

@app.route("/api/formats", methods=["POST"])
def api_formats():
    """Get available formats for a URL."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    data = request.json
    url = data.get("url")

    if not url:
        return {"error": "URL is required"}, 400

    try:
        from plugins.helper.upload import fetch_ytdlp_formats
        import concurrent.futures
        
        # Use ThreadPoolExecutor for timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                lambda: asyncio.run(fetch_ytdlp_formats(url))
            )
            try:
                res = future.result(timeout=15)
            except concurrent.futures.TimeoutError:
                # Return fallback options on timeout
                return jsonify({
                    "formats": [
                        {"format_id": "best", "label": "Best Quality"},
                        {"format_id": "1080p", "label": "1080p HD"},
                        {"format_id": "720p", "label": "720p HD"},
                        {"format_id": "480p", "label": "480p SD"},
                        {"format_id": "360p", "label": "360p"}
                    ]
                }), 200
        
        # Filter to only show downloadable video formats
        if 'formats' in res:
            filtered_formats = []
            seen_heights = set()
            
            for fmt in res['formats']:
                # Only include video formats with height
                if fmt.get('vcodec') != 'none' and fmt.get('height'):
                    height = fmt['height']
                    # Only show one format per height (best quality for that height)
                    if height not in seen_heights:
                        seen_heights.add(height)
                        label = f"{height}p"
                        if fmt.get('fps'):
                            label += f" ({fmt['fps']}fps)"
                        if fmt.get('filesize'):
                            size_mb = fmt['filesize'] / (1024 * 1024)
                            label += f" - {size_mb:.1f}MB"
                        filtered_formats.append({
                            "format_id": fmt.get('format_id', f"{height}p"),
                            "label": label,
                            "height": height
                        })
            
            # Sort by height descending
            filtered_formats.sort(key=lambda x: x['height'], reverse=True)
            
            # Add "Best Quality" option at the top
            filtered_formats.insert(0, {
                "format_id": "best",
                "label": "Best Quality",
                "height": 9999
            })
            
            res['formats'] = filtered_formats
        
        return jsonify(res), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/web-download", methods=["POST"])
def api_web_download():
    """Start a web download."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    data = request.json
    url = data.get("url")
    format_id = data.get("format_id", "direct")
    mode = data.get("mode", "direct")
    filename = data.get("filename")

    if not url:
        return {"error": "URL is required"}, 400

    download_id = str(uuid.uuid4())

    # Initialize progress
    DOWNLOAD_PROGRESS[download_id] = {
        "status": "queued",
        "percentage": 0,
        "action": "Queued",
        "speed": "-- MB/s",
        "_last_update": time.time()
    }

    # Start download in background thread
    from plugins.helper.upload import download_to_file

    def run_download():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(download_to_file(download_id, url, format_id, mode, filename))
        finally:
            loop.close()

    thread = threading.Thread(target=run_download, daemon=True)
    thread.start()

    return jsonify({"download_id": download_id}), 200

@app.route("/api/progress/<download_id>")
def api_progress(download_id):
    """Get download progress."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    progress = DOWNLOAD_PROGRESS.get(download_id)
    if not progress:
        return {"error": "Download not found"}, 404

    response_data = {
        "status": progress.get("status"),
        "percentage": progress.get("percentage", 0),
        "action": progress.get("action", ""),
        "speed": progress.get("speed", "-- MB/s")
    }

    # Add file info when download is complete
    if progress.get("status") == "complete":
        filepath = progress.get("filepath")
        if filepath and os.path.exists(filepath):
            response_data["filename"] = progress.get("filename", os.path.basename(filepath))
            response_data["filesize"] = os.path.getsize(filepath)
            response_data["filesize_human"] = humanbytes(os.path.getsize(filepath))

    return jsonify(response_data), 200

@app.route("/api/download-file/<download_id>")
def api_download_file(download_id):
    """Download the completed file."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    progress = DOWNLOAD_PROGRESS.get(download_id)
    if not progress or progress.get("status") != "complete":
        return {"error": "Download not complete"}, 404

    filepath = progress.get("filepath")
    filename = progress.get("filename")

    if not filepath or not os.path.exists(filepath):
        return {"error": "File not found"}, 404

    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route("/health")
def health():
    if app.is_shutting_down:
        return {"status": "shutting_down"}, 503
    if not app.is_ready:
        return {"status": "starting"}, 503
    return {"status": "ok"}, 200

# ── Admin Panel Routes ─────────────────────────────────────────────────────

@app.route("/admin")
def admin_panel():
    """Serve the admin panel HTML."""
    return send_from_directory("web_new", "admin.html")

def generate_token(username):
    """Generate JWT token for admin authentication."""
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route("/admin/login", methods=["POST"])
def admin_login():
    """Admin login endpoint."""
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = generate_token(username)
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    """Get overall statistics."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_token(token):
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "total_users": len(DOWNLOAD_PROGRESS),
        "total_downloads": TRAFFIC_STATS['total_downloads'],
        "data_transferred_gb": TRAFFIC_STATS['data_transferred_bytes'] / (1024**3),
        "active_downloads": len([d for d in DOWNLOAD_PROGRESS.values() if d.get('status') == 'downloading'])
    }), 200

@app.route("/admin/users", methods=["GET"])
def admin_users():
    """Get user information."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_token(token):
        return jsonify({"error": "Unauthorized"}), 401

    users = []
    for download_id, info in DOWNLOAD_PROGRESS.items():
        users.append({
            "user_id": download_id[:8],
            "downloads": 1 if info.get('status') == 'complete' else 0,
            "last_active": datetime.fromtimestamp(info.get('_last_update', time.time())).strftime('%Y-%m-%d %H:%M'),
            "active": info.get('status') == 'downloading'
        })

    return jsonify({"users": users}), 200

@app.route("/admin/traffic", methods=["GET"])
def admin_traffic():
    """Get traffic statistics."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_token(token):
        return jsonify({"error": "Unauthorized"}), 401

    today = datetime.now().strftime('%Y-%m-%d')
    
    return jsonify({
        "today": TRAFFIC_STATS['daily_stats'].get(today, 0),
        "week": sum(TRAFFIC_STATS['daily_stats'].values()),
        "month": sum(TRAFFIC_STATS['daily_stats'].values()),
        "avg_size_mb": (TRAFFIC_STATS['data_transferred_bytes'] / TRAFFIC_STATS['total_downloads'] / (1024**2)) if TRAFFIC_STATS['total_downloads'] > 0 else 0,
        "recent": TRAFFIC_STATS['recent_downloads'][-10:]
    }), 200

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    """Get or update site settings."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_token(token):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'GET':
        return jsonify(SITE_CONFIG), 200
    
    if request.method == 'POST':
        data = request.json
        SITE_CONFIG.update(data)
        return jsonify({"success": True}), 200

@app.route("/admin/change-password", methods=["POST"])
def admin_change_password():
    """Change admin password."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_token(token):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    new_password = data.get("password")
    
    if new_password:
        global ADMIN_PASSWORD
        ADMIN_PASSWORD = new_password
        return jsonify({"success": True}), 200
    
    return jsonify({"error": "Invalid password"}), 400

# ── Link API Endpoints (for external integration) ─────────────────────────────

@app.route("/grab", methods=["GET"])
def grab_get():
    """Extract direct media links from any video URL (GET)."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    url = request.args.get("url")
    if not url:
        return {"error": "URL is required"}, 400

    try:
        from plugins.helper.extractor import extract_links
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(extract_links(url))
        loop.close()
        return jsonify(res), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/grab", methods=["POST"])
def grab_post():
    """Extract direct media links from any video URL (POST)."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    data = request.json
    url = data.get("url")
    if not url:
        return {"error": "URL is required"}, 400

    try:
        from plugins.helper.extractor import extract_links
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(extract_links(url))
        loop.close()
        return jsonify(res), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/extract", methods=["POST"])
def extract():
    """Get full yt-dlp compatible extraction JSON."""
    if not app.is_ready:
        return {"error": "Server is not ready"}, 503

    data = request.json
    url = data.get("url")
    if not url:
        return {"error": "URL is required"}, 400

    try:
        from plugins.helper.upload import fetch_ytdlp_formats
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(fetch_ytdlp_formats(url))
        loop.close()
        return jsonify(res), 200
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # Mark app as ready immediately
    app.is_ready = True
    
    # Start background pruning task
    def run_prune_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(prune_progress_task())
        finally:
            loop.close()
    
    prune_thread = threading.Thread(target=run_prune_task, daemon=True)
    prune_thread.start()
    
    port = int(os.environ.get('PORT', 8080))
    workers = int(os.environ.get('WEB_WORKERS', 4))  # 4 workers on 12GB VPS

    try:
        # Use gunicorn in production for multi-worker performance
        from gunicorn.app.wsgiapp import WSGIApplication
        import sys
        sys.argv = [
            'gunicorn',
            '--bind', f'0.0.0.0:{port}',
            '--workers', str(workers),
            '--threads', '4',
            '--worker-class', 'gthread',
            '--timeout', '600',
            '--keep-alive', '5',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            'app_web:app'
        ]
        WSGIApplication().run()
    except ImportError:
        # Fallback to Flask dev server if gunicorn not available
        app.run(host="0.0.0.0", port=port, threaded=True)
