import os
import re
import ssl
import json
import uuid
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

CONFIG_FILE = Path(__file__).parent / "config.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Videos" / "Downloads"

SUPPORTED_PLATFORMS = [
    ("YouTube",      r"(youtube\.com|youtu\.be)",        "🎥"),
    ("TikTok",       r"tiktok\.com",                     "🎵"),
    ("Facebook",     r"(facebook\.com|fb\.watch)",        "👤"),
    ("Instagram",    r"instagram\.com",                   "📸"),
    ("Twitter / X",  r"(twitter\.com|x\.com)",           "🐦"),
    ("Reddit",       r"reddit\.com",                      "🔴"),
    ("Twitch",       r"twitch\.tv",                       "💜"),
    ("Vimeo",        r"vimeo\.com",                       "🎬"),
    ("Dailymotion",  r"dailymotion\.com",                 "▶️"),
    ("SoundCloud",   r"soundcloud\.com",                  "🎧"),
    ("Rumble",       r"rumble\.com",                      "📹"),
    ("Odysee",       r"odysee\.com",                      "🌊"),
    ("Bilibili",     r"bilibili\.com",                    "📺"),
    ("Kick",         r"kick\.com",                        "🎮"),
    ("Pinterest",    r"pinterest\.(com|de)",              "📌"),
    ("Spotify",      r"spotify\.com",                     "🎶"),
    ("Mixcloud",     r"mixcloud\.com",                    "🎼"),
    ("Streamable",   r"streamable\.com",                  "📡"),
    ("Twatter",      r"nitter\.",                         "🐤"),
    ("LinkedIn",     r"linkedin\.com",                    "💼"),
]


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"download_dir": str(DEFAULT_DOWNLOAD_DIR)}


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def get_download_dir() -> Path:
    path = Path(load_config().get("download_dir", str(DEFAULT_DOWNLOAD_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def detect_platform(url: str) -> tuple[str, str]:
    for name, pattern, icon in SUPPORTED_PLATFORMS:
        if re.search(pattern, url, re.IGNORECASE):
            return name, icon
    return "Andere", "🌐"


jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def _run_download(job_id: str, url: str, quality: str) -> None:
    dl_dir = get_download_dir()
    output_template = str(dl_dir / f"{job_id}_%(title).80s.%(ext)s")

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
                pct_str = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    jobs[job_id]["progress"] = float(pct_str)
                except ValueError:
                    pass
                jobs[job_id]["speed"] = d.get("_speed_str", "")
                jobs[job_id]["eta"] = d.get("_eta_str", "")
            elif d["status"] == "finished":
                jobs[job_id]["progress"] = 99

    ydl_opts = {
        "format": format_spec,
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
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

        files = sorted(dl_dir.glob(f"{job_id}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        filename = files[0].name if files else None

        with jobs_lock:
            jobs[job_id].update({
                "status": "done",
                "progress": 100,
                "filename": filename,
                "title": title,
                "dl_dir": str(dl_dir),
            })
    except Exception as e:
        with jobs_lock:
            jobs[job_id].update({"status": "error", "error": str(e)})


@app.route("/")
def index():
    cfg = load_config()
    return render_template("index.html",
                           platforms=SUPPORTED_PLATFORMS,
                           download_dir=cfg.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)))


@app.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(load_config())


@app.route("/settings", methods=["POST"])
def update_settings():
    data = request.json or {}
    cfg = load_config()
    if "download_dir" in data:
        cfg["download_dir"] = data["download_dir"]
    save_config(cfg)
    Path(cfg["download_dir"]).mkdir(parents=True, exist_ok=True)
    return jsonify({"ok": True, "config": cfg})


@app.route("/info", methods=["POST"])
def get_info():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "Keine URL angegeben"}), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                "noplaylist": True, "nocheckcertificate": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        platform, icon = detect_platform(url)
        return jsonify({
            "title":    info.get("title", "Unbekannt"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "platform": platform,
            "icon":     icon,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/download", methods=["POST"])
def start_download():
    data = request.json or {}
    url = data.get("url", "").strip()
    quality = data.get("quality", "best")
    if not url:
        return jsonify({"error": "Keine URL angegeben"}), 400

    job_id = uuid.uuid4().hex[:12]
    platform, icon = detect_platform(url)
    with jobs_lock:
        jobs[job_id] = {
            "status": "running", "progress": 0,
            "speed": "", "eta": "", "filename": None,
            "error": None, "platform": platform, "icon": icon,
        }

    threading.Thread(target=_run_download, args=(job_id, url, quality), daemon=True).start()
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
    dl_dir = Path(job.get("dl_dir", str(get_download_dir())))
    return send_from_directory(dl_dir, job["filename"], as_attachment=True)


@app.route("/cleanup/<job_id>", methods=["DELETE"])
def cleanup(job_id: str):
    with jobs_lock:
        job = jobs.pop(job_id, None)
    if job and job.get("filename"):
        dl_dir = Path(job.get("dl_dir", str(get_download_dir())))
        path = dl_dir / job["filename"]
        if path.exists():
            path.unlink()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print(f"Download-Ordner: {get_download_dir()}")
    print("Starte auf http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
