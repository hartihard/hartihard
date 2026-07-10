# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

VideoLoad / "KI Hub" is a video downloader wrapping `yt-dlp`, shipped as three independent front-ends over the same download logic, each duplicated rather than shared:

- `app.py` — Flask web app (browser UI, background jobs tracked in-memory, served on port 5000)
- `cli.py` — standalone terminal command (`videoload`), designed to drop videos straight into ComfyUI/Fooocus input folders for AI workflows
- `gui.py` — standalone Tkinter desktop app with the same target-folder concept

`templates/index.html` is a single self-contained HTML file (inline `<style>` and `<script>`, no build step, no separate JS/CSS assets) that talks to `app.py`'s JSON endpoints.

`install.sh` installs the CLI as `~/.local/bin/videoload` and registers a `.desktop` entry for the GUI. `video-downloader.service` is a systemd unit for running `app.py` as a background service (`WorkingDirectory=%h/hartihard`).

There are no tests, linter config, or CI in this repo.

## Running

```bash
pip install -r requirements.txt   # flask, yt-dlp (ffmpeg required separately for audio extraction/merging)

python3 app.py                    # web app at http://localhost:5000
python3 gui.py                    # desktop app (Tkinter)
python3 cli.py <URL> [--ziel comfyui|fooocus|videos|<path>] [--qualitaet best|1080|720|480|audio] [--info]

./install.sh                      # installs `videoload` CLI command + desktop entry system-wide
```

There is no build step, package manifest beyond `requirements.txt`, test suite, or linter — verify changes by running the relevant entry point directly.

## Architecture notes

- **Three parallel implementations, not shared code.** The download-options logic (quality → yt-dlp `format` string map, `nocheckcertificate`, SSL bypass via `ssl._create_default_https_context = ssl._create_unverified_context`, audio-extraction postprocessor config) is copy-pasted across `app.py`, `cli.py`, and `gui.py`. When changing download behavior (new quality option, new yt-dlp opt, new platform pattern), update all three unless the change is genuinely UI-specific.
- **`app.py` job model**: downloads run in daemon `threading.Thread`s, tracked in a module-level `jobs: dict[str, dict]` guarded by `jobs_lock`. State is in-memory only — restarting the process loses all in-flight/completed job records. The frontend polls `GET /status/<job_id>` after kicking off `POST /download`, then fetches the file via `GET /file/<job_id>` and calls `DELETE /cleanup/<job_id>` to remove it from disk/memory.
- **Config**: `app.py` persists only `download_dir` to `config.json` (gitignored) next to the script; read/written via `load_config`/`save_config`. `cli.py` and `gui.py` don't use this config file — they resolve target directories independently (`ZIELE` / `DEFAULT_ZIELE` dicts, checking for existing ComfyUI/Fooocus folders in common locations before falling back to creating one).
- **Platform detection**: `SUPPORTED_PLATFORMS` in `app.py` is a list of `(name, regex, emoji)` tuples matched against the URL via `detect_platform`; this list is presentational only (drives the UI's platform badge) and is independent of `cli.py`'s `ZIELE`/quality maps.
- **User-facing strings are German** (UI text, CLI help, error messages like "Keine URL angegeben"). Match this convention in user-visible strings; code identifiers are a mix of German (`ziel`, `qualitaet`) and English.
- **`templates/index.html`** has no separate static assets — CSS and JS live inline in the same file. When adding frontend behavior, edit this file directly rather than introducing a build pipeline.
