from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

# Cookies file path
COOKIES_FILE = os.path.join(os.path.dirname(__file__), 'cookies.txt')

def get_ydl_opts(extra={}):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    opts.update(extra)
    return opts

@app.route('/')
def home():
    cookies_ok = os.path.exists(COOKIES_FILE)
    return jsonify({
        "status": "VidSnap API running",
        "version": "2.0",
        "cookies": "loaded" if cookies_ok else "not found"
    })

@app.route('/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get("title", "Video"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def get_download_url():
    data = request.get_json()
    url = data.get('url', '').strip()
    fmt = data.get('format', 'mp4')
    quality = data.get('quality', '720')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if fmt == 'mp3':
        format_sel = 'bestaudio/best'
    elif fmt == 'mute':
        q = quality if quality != 'max' else 'best'
        format_sel = f'bestvideo[height<={q}][ext=mp4]/bestvideo'
    else:
        if quality == 'max':
            format_sel = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            format_sel = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]/best'

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts({'format': format_sel})) as ydl:
            info = ydl.extract_info(url, download=False)

            if 'requested_formats' in info:
                dl_url = info['requested_formats'][0]['url']
            elif 'url' in info:
                dl_url = info['url']
            else:
                return jsonify({"error": "Could not extract URL"}), 500

            return jsonify({
                "url": dl_url,
                "title": info.get("title", "video"),
                "ext": info.get("ext", "mp4"),
                "thumbnail": info.get("thumbnail", ""),
            })
    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        if 'Sign in' in err or 'bot' in err:
            return jsonify({"error": "YouTube bot check failed. Please add cookies.txt to the repo."}), 403
        if 'Private' in err:
            return jsonify({"error": "This video is private."}), 403
        return jsonify({"error": err[:200]}), 500
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
