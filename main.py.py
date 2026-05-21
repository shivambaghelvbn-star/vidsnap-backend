from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)  # Allow all frontend origins

@app.route('/')
def home():
    return jsonify({"status": "VidSnap API running", "version": "1.0"})

@app.route('/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get("title", "Video"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
                "view_count": info.get("view_count", 0),
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download', methods=['POST'])
def get_download_url():
    data = request.get_json()
    url = data.get('url', '').strip()
    fmt = data.get('format', 'mp4')       # mp4 | mp3 | mute | gif
    quality = data.get('quality', '720')  # 360 | 480 | 720 | 1080 | max

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Build format selector
    if fmt == 'mp3':
        format_sel = 'bestaudio/best'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif fmt == 'mute':
        q = quality if quality != 'max' else 'best'
        format_sel = f'bestvideo[height<={q}][ext=mp4]/bestvideo[height<={q}]/bestvideo'
        postprocessors = []
    else:
        if quality == 'max':
            format_sel = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            format_sel = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[height<={quality}]/best'
        postprocessors = []

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': format_sel,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Get the best matching URL
            if 'requested_formats' in info:
                # Merged format - return both URLs for client info
                video_url = info['requested_formats'][0]['url']
                audio_url = info['requested_formats'][1]['url'] if len(info['requested_formats']) > 1 else None
                dl_url = video_url  # Primary
            elif 'url' in info:
                dl_url = info['url']
                audio_url = None
            else:
                return jsonify({"error": "Could not extract download URL"}), 500

            return jsonify({
                "url": dl_url,
                "audio_url": audio_url,
                "title": info.get("title", "video"),
                "ext": info.get("ext", "mp4"),
                "filesize": info.get("filesize") or info.get("filesize_approx", 0),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
            })
    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        if 'Private video' in err:
            return jsonify({"error": "This video is private."}), 403
        if 'age' in err.lower():
            return jsonify({"error": "Age-restricted video. Cannot download."}), 403
        return jsonify({"error": "Download failed: " + err[:200]}), 500
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
