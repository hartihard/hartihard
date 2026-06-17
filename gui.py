#!/usr/bin/env python3
"""
KI Hub – Desktop App
Video Downloader mit ComfyUI & Fooocus Integration
"""
import ssl
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

# ── Farben ─────────────────────────────────────────────────────────────────
BG        = "#0d0d18"
BG2       = "#13131f"
BG3       = "#1c1c2e"
BORDER    = "#2d2d44"
ACCENT    = "#a855f7"
ACCENT2   = "#7c3aed"
GREEN     = "#10b981"
RED       = "#ef4444"
TEXT      = "#e2e8f0"
TEXT2     = "#94a3b8"
MUTED     = "#475569"
FONT      = ("Segoe UI", 10)
FONT_B    = ("Segoe UI", 10, "bold")
FONT_H    = ("Segoe UI", 14, "bold")
FONT_SM   = ("Segoe UI", 8)

DEFAULT_ZIELE = {
    "ComfyUI":  Path.home() / "ComfyUI" / "input",
    "Fooocus":  Path.home() / "Fooocus" / "inputs",
    "Videos":   Path.home() / "Videos" / "Downloads",
}


class KIHubApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KI Hub – Video Downloader")
        self.geometry("700x580")
        self.minsize(600, 500)
        self.configure(bg=BG)
        self.resizable(True, True)

        # Icon (falls vorhanden)
        try:
            self.iconbitmap()
        except Exception:
            pass

        self._job_running = False
        self._selected_target = tk.StringVar(value="Videos")
        self._quality = tk.StringVar(value="best")
        self._custom_path = tk.StringVar(value=str(DEFAULT_ZIELE["Videos"]))

        self._build_ui()
        self._update_path_label()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG, pady=16)
        hdr.pack(fill="x", padx=24)
        tk.Label(hdr, text="⬇  KI Hub", font=("Segoe UI", 18, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(hdr, text="Video Downloader", font=FONT, bg=BG, fg=TEXT2).pack(
            side="left", padx=(8, 0), pady=(4, 0))

        self._sep(self)

        # URL
        url_frame = tk.Frame(self, bg=BG, padx=24, pady=10)
        url_frame.pack(fill="x")
        tk.Label(url_frame, text="Video-URL", font=FONT_B, bg=BG, fg=TEXT2).pack(anchor="w")
        row = tk.Frame(url_frame, bg=BG)
        row.pack(fill="x", pady=(4, 0))
        self._url_var = tk.StringVar()
        url_entry = tk.Entry(row, textvariable=self._url_var,
                             font=FONT, bg=BG3, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, highlightthickness=2,
                             highlightbackground=BORDER, highlightcolor=ACCENT)
        url_entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)
        url_entry.bind("<Return>", lambda e: self._start())

        tk.Button(row, text="Einfugen", font=FONT_SM, bg=BG3, fg=TEXT2,
                  activebackground=ACCENT, activeforeground="white",
                  relief="flat", cursor="hand2", padx=10,
                  command=self._paste).pack(side="left", padx=(6, 0), ipady=6)
        tk.Button(row, text="✕", font=FONT_SM, bg=BG3, fg=MUTED,
                  activebackground=RED, activeforeground="white",
                  relief="flat", cursor="hand2", padx=8,
                  command=lambda: self._url_var.set("")).pack(side="left", padx=(4, 0), ipady=6)

        self._sep(self)

        # Ziel-Auswahl
        ziel_frame = tk.Frame(self, bg=BG, padx=24, pady=10)
        ziel_frame.pack(fill="x")
        tk.Label(ziel_frame, text="Speichern in", font=FONT_B, bg=BG, fg=TEXT2).pack(anchor="w")
        btn_row = tk.Frame(ziel_frame, bg=BG)
        btn_row.pack(fill="x", pady=(8, 6))

        self._target_btns = {}
        targets = [
            ("ComfyUI", "🎨"),
            ("Fooocus",  "✨"),
            ("Videos",   "📁"),
            ("Eigener",  "📂"),
        ]
        for name, icon in targets:
            b = tk.Button(btn_row, text=f"{icon}  {name}",
                          font=FONT_B, relief="flat", cursor="hand2",
                          padx=14, pady=8,
                          command=lambda n=name: self._select_target(n))
            b.pack(side="left", padx=(0, 6))
            self._target_btns[name] = b

        self._path_label = tk.Label(ziel_frame, text="", font=FONT_SM, bg=BG, fg=MUTED)
        self._path_label.pack(anchor="w")
        self._select_target("Videos")

        self._sep(self)

        # Qualitat
        q_frame = tk.Frame(self, bg=BG, padx=24, pady=10)
        q_frame.pack(fill="x")
        tk.Label(q_frame, text="Qualitat", font=FONT_B, bg=BG, fg=TEXT2).pack(anchor="w")
        q_row = tk.Frame(q_frame, bg=BG)
        q_row.pack(fill="x", pady=(6, 0))

        self._q_btns = {}
        quals = [("⭐ Beste", "best"), ("1080p", "1080"), ("720p", "720"),
                 ("480p", "480"), ("🎵 Audio MP3", "audio")]
        for label, val in quals:
            b = tk.Button(q_row, text=label, font=FONT_SM, relief="flat",
                          cursor="hand2", padx=10, pady=6,
                          command=lambda v=val: self._select_quality(v))
            b.pack(side="left", padx=(0, 5))
            self._q_btns[val] = b
        self._select_quality("best")

        self._sep(self)

        # Download Button
        dl_frame = tk.Frame(self, bg=BG, padx=24, pady=12)
        dl_frame.pack(fill="x")
        self._dl_btn = tk.Button(
            dl_frame, text="⬇   Herunterladen",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT2, fg="white", activebackground=ACCENT,
            activeforeground="white", relief="flat", cursor="hand2",
            pady=12, command=self._start)
        self._dl_btn.pack(fill="x")

        # Progress
        prog_frame = tk.Frame(self, bg=BG, padx=24)
        prog_frame.pack(fill="x", pady=(0, 4))
        self._prog = ttk.Progressbar(prog_frame, mode="determinate", length=100)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=BG3, background=ACCENT,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT2)
        self._prog.pack(fill="x")

        self._status_var = tk.StringVar(value="Bereit.")
        self._status = tk.Label(self, textvariable=self._status_var,
                                font=FONT_SM, bg=BG, fg=TEXT2,
                                wraplength=650, justify="left")
        self._status.pack(padx=24, pady=(4, 0), anchor="w")

        self._sep(self)

        # Log
        log_frame = tk.Frame(self, bg=BG, padx=24, pady=8)
        log_frame.pack(fill="both", expand=True)
        tk.Label(log_frame, text="Verlauf", font=FONT_B, bg=BG, fg=MUTED).pack(anchor="w")
        self._log = tk.Text(log_frame, font=FONT_SM, bg=BG2, fg=TEXT2,
                            relief="flat", bd=0, state="disabled",
                            highlightthickness=1, highlightbackground=BORDER,
                            height=6)
        self._log.pack(fill="both", expand=True, pady=(6, 0))

    def _sep(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=24, pady=2)

    # ── Steuerung ──────────────────────────────────────────────────────────

    def _paste(self):
        try:
            txt = self.clipboard_get()
            self._url_var.set(txt.strip())
        except Exception:
            pass

    def _select_target(self, name: str):
        self._selected_target.set(name)
        for n, b in self._target_btns.items():
            if n == name:
                b.configure(bg=ACCENT2, fg="white")
            else:
                b.configure(bg=BG3, fg=TEXT2)

        if name == "Eigener":
            path = filedialog.askdirectory(title="Download-Ordner wahlen")
            if path:
                self._custom_path.set(path)
            else:
                self._selected_target.set("Videos")
                self._select_target("Videos")
                return

        self._update_path_label()

    def _update_path_label(self):
        name = self._selected_target.get()
        if name == "Eigener":
            p = self._custom_path.get()
        else:
            p = str(DEFAULT_ZIELE.get(name, DEFAULT_ZIELE["Videos"]))
        self._path_label.configure(text=f"  →  {p}")

    def _select_quality(self, val: str):
        self._quality.set(val)
        for v, b in self._q_btns.items():
            if v == val:
                b.configure(bg=ACCENT2, fg="white")
            else:
                b.configure(bg=BG3, fg=TEXT2)

    def _get_target_path(self) -> Path:
        name = self._selected_target.get()
        if name == "Eigener":
            p = Path(self._custom_path.get())
        else:
            p = DEFAULT_ZIELE.get(name, DEFAULT_ZIELE["Videos"])
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ── Download ───────────────────────────────────────────────────────────

    def _start(self):
        if self._job_running:
            return
        url = self._url_var.get().strip()
        if not url:
            self._status_var.set("Bitte eine URL eingeben.")
            return

        self._job_running = True
        self._dl_btn.configure(state="disabled", bg=MUTED)
        self._prog["value"] = 0
        self._status_var.set("Starte …")

        t = threading.Thread(target=self._download_thread, args=(url,), daemon=True)
        t.start()

    def _download_thread(self, url: str):
        try:
            import yt_dlp
        except ImportError:
            self._done_ui("error", "yt-dlp nicht installiert. Bitte: pip install yt-dlp")
            return

        quality = self._quality.get()
        fmt_map = {
            "best":  "bestvideo+bestaudio/best",
            "1080":  "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "720":   "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "480":   "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "audio": "bestaudio/best",
        }
        target = self._get_target_path()
        output = str(target / "%(title).80s.%(ext)s")

        opts = {
            "format": fmt_map.get(quality, fmt_map["best"]),
            "outtmpl": output,
            "nocheckcertificate": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        if quality == "audio":
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
            opts["merge_output_format"] = None

        def hook(d):
            if d["status"] == "downloading":
                try:
                    pct = float(d.get("_percent_str", "0%").strip().replace("%", ""))
                except Exception:
                    pct = 0
                spd = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()
                self.after(0, lambda: self._update_progress(pct, spd, eta))
            elif d["status"] == "finished":
                self.after(0, lambda: self._update_progress(99, "", "Fertigstellen …"))

        opts["progress_hooks"] = [hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", url)
            msg = f"✅ Fertig: {title}\n   Gespeichert in: {target}"
            self._done_ui("ok", msg)
            self._log_add(f"✅ {title}  →  {self._selected_target.get()}")
        except Exception as e:
            self._done_ui("error", f"Fehler: {e}")
            self._log_add(f"❌ Fehler: {e}")

    def _update_progress(self, pct: float, speed: str, eta: str):
        self._prog["value"] = pct
        info = f"{pct:.0f}%"
        if speed:
            info += f"  {speed}"
        if eta:
            info += f"  ETA {eta}"
        self._status_var.set(info)

    def _done_ui(self, kind: str, msg: str):
        self._job_running = False
        self._prog["value"] = 100 if kind == "ok" else 0
        self._status_var.set(msg)
        self._dl_btn.configure(state="normal", bg=ACCENT2)

    def _log_add(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")


def main():
    app = KIHubApp()
    app.mainloop()


if __name__ == "__main__":
    main()
