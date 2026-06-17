#!/usr/bin/env python3
"""
VideoLoad CLI — Videos direkt in ComfyUI, Fooocus oder eigenen Ordner laden.
Verwendung: videoload <URL> [--ziel comfyui|fooocus|<pfad>] [--qualitaet best|1080|720|480|audio]
"""
import argparse
import sys
import ssl
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

ZIELE = {
    "comfyui": [
        Path.home() / "ComfyUI" / "input",
        Path.home() / "comfyui" / "input",
        Path.home() / "stable-diffusion-webui" / "inputs",
    ],
    "fooocus": [
        Path.home() / "Fooocus" / "inputs",
        Path.home() / "fooocus" / "inputs",
        Path.home() / "Fooocus" / "outputs",
    ],
    "videos": Path.home() / "Videos" / "Downloads",
}

QUALITAETEN = {
    "best":  "bestvideo+bestaudio/best",
    "1080":  "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720":   "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480":   "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "audio": "bestaudio/best",
}


def find_ziel(name: str) -> Path:
    if name in ("comfyui", "fooocus"):
        for p in ZIELE[name]:
            if p.exists():
                return p
        # Ordner anlegen wenn nicht vorhanden
        path = ZIELE[name][0]
        path.mkdir(parents=True, exist_ok=True)
        print(f"  Ordner erstellt: {path}")
        return path
    elif name == "videos":
        p = ZIELE["videos"]
        p.mkdir(parents=True, exist_ok=True)
        return p
    else:
        p = Path(name).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p


def download(url: str, ziel: Path, qualitaet: str, audio_only: bool = False) -> None:
    try:
        import yt_dlp
    except ImportError:
        print("FEHLER: yt-dlp nicht installiert. Bitte: pip install yt-dlp")
        sys.exit(1)

    fmt = QUALITAETEN.get(qualitaet, QUALITAETEN["best"])
    output = str(ziel / "%(title).80s.%(ext)s")

    opts = {
        "format": fmt,
        "outtmpl": output,
        "nocheckcertificate": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }

    if qualitaet == "audio":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        opts["merge_output_format"] = None

    def hook(d):
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "").strip()
            spd = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "").strip()
            bar_len = 30
            try:
                filled = int(float(pct.replace("%", "")) / 100 * bar_len)
            except Exception:
                filled = 0
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r  [{bar}] {pct:>6}  {spd:>10}  ETA {eta:>6}", end="", flush=True)
        elif d["status"] == "finished":
            print(f"\r  [{'█'*30}] 100%   Fertig!              ")

    opts["progress_hooks"] = [hook]

    print(f"\n  URL:     {url}")
    print(f"  Ziel:    {ziel}")
    print(f"  Qualitat: {qualitaet}\n")

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "?")

    print(f"\n  Titel: {title}")
    print(f"  Gespeichert in: {ziel}\n")


def main():
    p = argparse.ArgumentParser(
        description="VideoLoad – Video Downloader fur ComfyUI, Fooocus & mehr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  videoload https://youtube.com/watch?v=...
  videoload https://tiktok.com/... --ziel comfyui
  videoload https://vimeo.com/... --ziel fooocus
  videoload https://x.com/... --ziel ~/KI/Videos
  videoload https://soundcloud.com/... --qualitaet audio
        """
    )
    p.add_argument("url", help="Video-URL")
    p.add_argument("--ziel", "-z", default="videos",
                   help="comfyui | fooocus | videos | /eigener/pfad  (Standard: videos)")
    p.add_argument("--qualitaet", "-q", default="best",
                   choices=["best", "1080", "720", "480", "audio"],
                   help="Videoqualitat (Standard: best)")
    p.add_argument("--info", "-i", action="store_true",
                   help="Nur Info anzeigen, nicht herunterladen")

    args = p.parse_args()

    if args.info:
        try:
            import yt_dlp
            ssl._create_default_https_context = ssl._create_unverified_context
            with yt_dlp.YoutubeDL({"quiet": True, "nocheckcertificate": True}) as ydl:
                info = ydl.extract_info(args.url, download=False)
            print(f"\nTitel:    {info.get('title')}")
            print(f"Kanal:    {info.get('uploader')}")
            print(f"Dauer:    {info.get('duration', 0)} Sekunden")
            print(f"Aufrufe:  {info.get('view_count', '?')}\n")
        except Exception as e:
            print(f"Fehler: {e}")
        return

    ziel_path = find_ziel(args.ziel)
    download(args.url, ziel_path, args.qualitaet)


if __name__ == "__main__":
    main()
