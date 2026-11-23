---
name: yt-dlp
description: "yt-dlp downloads: video, audio, subs, clips, playlists."
version: 1.0.0
author: chrismok-win11
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [yt-dlp, Video, Audio, Download, Media]
    related_skills: [youtube-content]
---

# yt-dlp Harness

## When to use

Use when the user wants to download/extract a video or audio file from a URL (YouTube or any of the thousands of supported sites), inspect available formats/subtitles, cut a clip/chapter, batch-download a playlist or URL list, or manage YouTube login cookies.

For YouTube transcripts/summaries without a file, prefer the youtube-content skill.

## Environment (this host)

- Binary: `C:\Users\14843\bin\yt-dlp.exe`, v2026.10.26 (stable channel, pinned), on PATH — invoke as `yt-dlp`.
- ffmpeg + ffprobe: on PATH at `C:\ProgramData\ffmpeg-master-latest-win64-gpl-shared\bin` — required for merging/converting/clipping.
- deno and node are on PATH (JS runtimes for yt-dlp-ejs = full YouTube support).
- Default output dir: `C:\Users\14843\Downloads\yt-dlp` (override with `--out DIR` or env `YTDLP_OUT`). Default cookies file: `<out dir>\cookies.txt`.
- Do NOT run `yt-dlp -U` unless the user asks; channel/version changes are a user decision.

## Harness

`SKILL_DIR` is the directory containing this SKILL.md. The helper builds the yt-dlp command, quotes URLs correctly, and prints exactly one JSON object to stdout:

```json
{"ok": true, "code": 0, "cmd": [...], "files": ["C:/abs/path.mp4"], "info": [...], "out": "...", "err": "..."}
```

`files` = final media file plus existing companions (.info.json, .srt, thumbnail). `info` is present only for the `info` command.

Commands:

```bash
python SKILL_DIR/scripts/yt.py version
python SKILL_DIR/scripts/yt.py info URL...            # metadata JSON per URL, no download
python SKILL_DIR/scripts/yt.py formats URL            # format table
python SKILL_DIR/scripts/yt.py subs URL               # manual + auto caption tables
python SKILL_DIR/scripts/yt.py download URL...        # mp4 video + info.json + en subs
python SKILL_DIR/scripts/yt.py audio URL...           # mp3 by default
python SKILL_DIR/scripts/yt.py clip URL --section SPEC...   # e.g. "Intro" "01:20-02:00"
python SKILL_DIR/scripts/yt.py playlist URL --items 1:5,8   # -I + download archive
python SKILL_DIR/scripts/yt.py batch FILE             # one URL per line
python SKILL_DIR/scripts/yt.py cookies export --browser chrome [--profile "Profile 1"] [--file PATH] [--all]
python SKILL_DIR/scripts/yt.py cookies check FILE
```

Options (any command): `--out DIR`, `--extra "RAW YT-DLP ARGS"` (repeatable; append raw flags, e.g. `--extra "-f best[height<=720]"`), `--timeout N` (default 1800 s), `--bin PATH`.

Download-family options: `--format mp4|mkv|webm|best` (video), `--format mp3|m4a|wav|aac|opus|vorbis|flac|alac|best` (audio), `--no-subs`, `--subs "en.*,ja"`, `--no-info-json`, `--thumb`, `--sponsorblock "sponsor,intro"` (removes those categories), `--cookies FILE`, `--cookies-from-browser BROWSER`, `--limit-rate 2M`, `--retries N`. Playlist/batch: `--no-archive` to disable the incremental archive file.

## Workflow

1. Run `info` first — cheap check the URL works; read title, duration_string, channel, subtitle languages.
2. If the video is login-gated (private / members-only / age-restricted) or the user says "use my cookies": run `cookies check` on the default cookies file first. If missing/stale, `cookies export` (see below) or ask the user.
3. Pick the command; use the default dir unless the user names one.
4. Run via `terminal` (long downloads: raise --timeout or use terminal background + process_manage).
5. Verify: `ok=true`, `files` non-empty, and each file exists with size > 0.
6. Report the absolute file paths as plain text.

## Cookies (YouTube login)

Standard source on this host: Chrome (user-chosen), via Netscape `cookies.txt` files.

- Export: `yt.py cookies export --browser chrome` — writes `<out dir>\cookies.txt`, filtered to youtube.com/google.com domains (pass `--all` to keep every site; `--profile "Profile 1"` for a named profile). Chrome must be FULLY closed first; the script detects a running Chrome and reports `browser_running` with a hint. If the user does not close Chrome, suggest the "Get cookies.txt LOCALLY" extension instead.
- Verify: `yt.py cookies check FILE` — reports the key cookies (SAPISID, APISID, SID, HSID, SSID, YTLID, LOGIN_INFO, GOOGLE_SESS, HE), which are missing, and expiry of each.
- Use: any download-family command with `--cookies <FILE>`; or `--cookies-from-browser chrome` directly when Chrome is closed.
- Chrome 127+ quirk (app-bound encryption): direct extraction can fail even with Chrome closed ("Could not copy Chrome cookie database" / failed decrypts). Then: export via the extension, or use Firefox (reads while open, no lock — `--browser firefox`).
- What cookies fix: private, members-only, age-restricted (account must be age-verified). What they do NOT fix: "Sign in to confirm you're not a bot" / 429 — those need fresh cookies within ~30 min of a CAPTCHA, same IP, and optionally the browser's User-Agent via `--extra "--add-headers \"User-Agent: ...\""`.
- Alternative (no cookies): YouTube supports direct login — `--extra "--username USER --password PASS"` (add `-2 CODE` for 2FA) via the harness.
- Treat cookies files as secrets (they are full session tokens).

## Defaults baked in (user-chosen)

- download: mp4 (native mp4 v+a preferred, merged fallback), plus `.info.json` and English subtitles (manual + auto) as `.srt` (`--sub-langs en`; broaden with `--subs "en.*,ja"` if needed — more languages = more caption requests = higher 429 risk)
- audio: mp3, best VBR (`--audio-quality 0`), thumbnail + metadata embedded
- cookies source: Chrome
- always: `--ignore-config --no-update --no-progress --newline -q --no-simulate`, `--windows-filenames` (Windows), title trimmed to 120 bytes

## Pitfalls

- If running yt-dlp directly (not via the harness): quote URLs in the shell (`&` breaks unquoted URLs); in .bat files double the `%` in `-o` templates (`%%(title)s`).
- Hi-res YouTube streams are separate video+audio — merging needs ffmpeg (installed here).
- Cloudflare 403 = pass `--cookies` plus the browser's full User-Agent via `--add-headers "User-Agent: ..."`.
- Clips cut at keyframes (fast). Frame-accurate cut = add `--extra "--force-keyframes-at-cuts"` (re-encodes, slow).
- Re-running playlist/batch is incremental via `yt-dlp-archive.txt` in the out dir; delete it to re-download everything.
- If a site breaks on the stable build: ask the user, then try `yt-dlp --update-to nightly` (or check the repo's issue tracker) — do not switch channels silently.
- Raw `--print` implies `--simulate`; add `--no-simulate` when you actually want files.

## Updates

Pinned: stable 2026.10.26. On user request: `yt-dlp --update` (same channel) or `yt-dlp --update-to nightly` / `stable@TAG`; verify with `--version`. Manual reinstall: download `yt-dlp.exe` + `SHA2-256SUMS` from the release, verify the hash, place in `C:\Users\14843\bin`.

## Reference

`references/options-cheatsheet.md` — full option groups, format-selection syntax, output-template fields, post-processing, preset aliases, WHEN values for `--print`, FAQ pitfalls. Consult it for anything the harness flags don't cover, then pass the raw flag via `--extra`.

## TODO

- Linux version (this skill is currently Windows-only): port to Linux hosts — install the release binary `yt-dlp` (zipimport, needs Python 3.11+) or `pip install yt-dlp`; ffmpeg/ffprobe on PATH; verify `cookies-from-browser` under Linux keyrings (gnomekeyring/kwallet/basictext; over SSH the keyring is often not unlocked — prefer exporting `cookies.txt`); cookies files use LF newlines (CRLF = HTTP 400); re-run the smoke-test suite from this host; then widen the `platforms` frontmatter and move the Windows-specific Environment facts into per-host notes. `scripts/yt.py` is already stdlib-only and cross-platform — the Windows-specific parts live in the SKILL.md Environment section, the `--windows-filenames` default, and the taskkill hint.
