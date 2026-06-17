import os
import re
import uuid
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Track active download jobs: job_id -> {status, progress, filename, error}
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()

SUPPORTED_PLATFORMS = [
    ("YouTube", r"(youtube\.com|youtu\.be)"),
    ("TikTok", r"tiktok\.com"),
    ("Facebook", r"(facebook\.com|fb\.watch)"),
    ("Instagram", r"instagram\.com"),
    ("Twitter / X", r"(twitter\.com|x\.com)"),
    ("Reddit", r"reddit\.com"),
    ("Twitch", r"twitch\.tv"),
    ("Vimeo", r"vimeo\.com"),
    ("Dailymotion", r"dailymotion\.com"),
]


def detect_platform(url: str) -> str:
    for name, pattern in SUPPORTED_PLATFORMS:
        if re.search(pattern, url, re.IGNORECASE):
            return name
    return "Andere Plattform"


def _run_download(job_id: str, url: str, quality: str) -> None:
    output_template = str(DOWNLOAD_DIR / f"{job_id}_%(title).80s.%(ext)s")

    format_spec = "bestvideo+bestaudio/best"
    if quality == "1080":
        format_spec = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
    elif quality == "720":
        format_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
    elif quality == "480":
        format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
    elif quality == "audio":
        format_spec = "bestaudio/best"

    def progress_hook(d):
        with jobs_lock:
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    jobs[job_id]["progress"] = float(pct)
                except ValueError:
                    pass
                jobs[job_id]["speed"] = d.get("_speed_str", "")
                jobs[job_id]["eta"] = d.get("_eta_str", "")
            elif d["status"] == "finished":
                jobs[job_id]["progress"] = 99
                jobs[job_id]["filename_raw"] = d.get("filename", "")

    ydl_opts = {
        "format": format_spec,
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "postprocessors": [],
    }

    if quality == "audio":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        ydl_opts["merge_output_format"] = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Video")

        # Find the file that was actually written
        files = sorted(DOWNLOAD_DIR.glob(f"{job_id}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        filename = files[0].name if files else None

        with jobs_lock:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["filename"] = filename
            jobs[job_id]["title"] = title

    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)


@app.route("/")
def index():
    return render_template("index.html", platforms=SUPPORTED_PLATFORMS)


@app.route("/info", methods=["POST"])
def get_info():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "Keine URL angegeben"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({
            "title": info.get("title", "Unbekannt"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "platform": detect_platform(url),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/download", methods=["POST"])
def start_download():
    url = request.json.get("url", "").strip()
    quality = request.json.get("quality", "best")

    if not url:
        return jsonify({"error": "Keine URL angegeben"}), 400

    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {"status": "running", "progress": 0, "speed": "", "eta": "", "filename": None, "error": None}

    thread = threading.Thread(target=_run_download, args=(job_id, url, quality), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job nicht gefunden"}), 404
    return jsonify(job)


@app.route("/file/<job_id>")
def download_file(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job["status"] != "done" or not job["filename"]:
        return jsonify({"error": "Datei nicht bereit"}), 404
    return send_from_directory(DOWNLOAD_DIR, job["filename"], as_attachment=True)


@app.route("/cleanup/<job_id>", methods=["DELETE"])
def cleanup(job_id: str):
    with jobs_lock:
        job = jobs.pop(job_id, None)
    if job and job.get("filename"):
        path = DOWNLOAD_DIR / job["filename"]
        if path.exists():
            path.unlink()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
