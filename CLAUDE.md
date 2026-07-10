# CLAUDE.md

Diese Datei bietet Claude Code (claude.ai/code) Orientierungshilfe für die Arbeit mit dem Code in diesem Repository.

## Projektübersicht

VideoLoad / "KI Hub" ist ein Video-Downloader auf Basis von `yt-dlp`, der als drei unabhängige Frontends mit derselben Download-Logik ausgeliefert wird — dupliziert statt geteilt:

- `app.py` — Flask-Web-App (Browser-UI, Hintergrund-Jobs im Speicher verwaltet, läuft auf Port 5000)
- `cli.py` — eigenständiger Terminal-Befehl (`videoload`), gedacht um Videos direkt in ComfyUI/Fooocus-Input-Ordner für KI-Workflows zu laden
- `gui.py` — eigenständige Tkinter-Desktop-App mit demselben Zielordner-Konzept

`templates/index.html` ist eine einzelne, in sich geschlossene HTML-Datei (inline `<style>` und `<script>`, kein Build-Schritt, keine separaten JS/CSS-Assets), die mit den JSON-Endpunkten von `app.py` kommuniziert.

`install.sh` installiert die CLI als `~/.local/bin/videoload` und registriert einen `.desktop`-Eintrag für die GUI. `video-downloader.service` ist eine systemd-Unit, um `app.py` als Hintergrunddienst laufen zu lassen (`WorkingDirectory=%h/hartihard`).

Es gibt keine Tests, keine Linter-Konfiguration und keine CI in diesem Repo.

## Ausführen

```bash
pip install -r requirements.txt   # flask, yt-dlp (ffmpeg wird separat für Audio-Extraktion/Merging benötigt)

python3 app.py                    # Web-App unter http://localhost:5000
python3 gui.py                    # Desktop-App (Tkinter)
python3 cli.py <URL> [--ziel comfyui|fooocus|videos|<pfad>] [--qualitaet best|1080|720|480|audio] [--info]

./install.sh                      # installiert den `videoload`-Befehl + Desktop-Eintrag systemweit
```

Es gibt keinen Build-Schritt, kein Package-Manifest außer `requirements.txt`, keine Test-Suite und keinen Linter — Änderungen werden verifiziert, indem der jeweilige Einstiegspunkt direkt ausgeführt wird.

## Architektur-Hinweise

- **Drei parallele Implementierungen, kein gemeinsamer Code.** Die Download-Options-Logik (Qualität → yt-dlp-`format`-String-Map, `nocheckcertificate`, SSL-Bypass via `ssl._create_default_https_context = ssl._create_unverified_context`, Audio-Extraktions-Postprocessor-Konfiguration) ist über `app.py`, `cli.py` und `gui.py` hinweg kopiert. Bei Änderungen am Download-Verhalten (neue Qualitätsstufe, neue yt-dlp-Option, neues Plattform-Muster) alle drei aktualisieren, außer die Änderung ist rein UI-spezifisch.
- **Job-Modell in `app.py`**: Downloads laufen in daemon-`threading.Thread`s, verwaltet in einem modul-globalen `jobs: dict[str, dict]`, abgesichert durch `jobs_lock`. Der Zustand liegt nur im Speicher — ein Neustart des Prozesses verwirft alle laufenden/abgeschlossenen Job-Datensätze. Das Frontend pollt `GET /status/<job_id>`, nachdem es `POST /download` angestoßen hat, holt die Datei dann über `GET /file/<job_id>` und ruft `DELETE /cleanup/<job_id>` auf, um sie von Platte und aus dem Speicher zu entfernen.
- **Konfiguration**: `app.py` persistiert ausschließlich `download_dir` in `config.json` (gitignored) neben dem Skript; gelesen/geschrieben über `load_config`/`save_config`. `cli.py` und `gui.py` nutzen diese Config-Datei nicht — sie lösen Zielordner unabhängig auf (`ZIELE`- / `DEFAULT_ZIELE`-Dicts, die zunächst prüfen, ob bereits ComfyUI-/Fooocus-Ordner an gängigen Orten existieren, bevor ein neuer angelegt wird).
- **Plattform-Erkennung**: `SUPPORTED_PLATFORMS` in `app.py` ist eine Liste von `(Name, Regex, Emoji)`-Tupeln, die per `detect_platform` gegen die URL geprüft werden; diese Liste ist rein präsentationsbezogen (steuert das Plattform-Badge in der UI) und unabhängig von den `ZIELE`-/Qualitäts-Maps in `cli.py`.
- **Nutzersichtbare Texte sind auf Deutsch** (UI-Text, CLI-Hilfe, Fehlermeldungen wie "Keine URL angegeben"). Diese Konvention bei nutzersichtbaren Strings beibehalten; Code-Bezeichner sind eine Mischung aus Deutsch (`ziel`, `qualitaet`) und Englisch.
- **`templates/index.html`** hat keine separaten statischen Assets — CSS und JS liegen inline in derselben Datei. Bei neuem Frontend-Verhalten diese Datei direkt bearbeiten statt eine Build-Pipeline einzuführen.
