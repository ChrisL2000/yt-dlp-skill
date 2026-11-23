# yt-dlp skill (Hermes Agent)

A [Hermes Agent](https://github.com/NousResearch/Hermes-Agent) skill plus a dependency-free Python harness for [yt-dlp](https://github.com/yt-dlp/yt-dlp): download/extract video and audio from YouTube or any of the thousands of sites yt-dlp supports, inspect formats and subtitles, cut clips by chapter or time range, batch-download playlists, and manage YouTube login cookies.

Built and tested on Windows 11 (Docker Desktop host, yt-dlp 2026.10.26 stable). The harness itself (`scripts/yt.py`) is stdlib-only and cross-platform; the skill documentation is currently Windows-oriented (see TODO below).

## Repo layout

- `SKILL.md` — the Hermes skill (agent-facing: workflow, defaults, pitfalls)
- `scripts/yt.py` — the CLI harness (Python 3, stdlib only — no pip installs)
- `references/options-cheatsheet.md` — condensed yt-dlp options reference (v2026.10.26): format selection, output templates, post-processing, preset aliases, `--print` WHEN values

## Install

1. **yt-dlp** (the skill targets the stable channel; pin the version you install):
   - Windows: download `yt-dlp.exe` from the [releases](https://github.com/yt-dlp/yt-dlp/releases), place it on PATH (e.g. `C:\Users\<you>\bin\yt-dlp.exe`)
   - macOS/Linux: `pip install yt-dlp` or the release binary (zipimport; needs Python 3.11+)
2. **ffmpeg + ffprobe** on PATH — required for merging hi-res video+audio, audio conversion, and clips.
3. **Optional env vars**:
   - `YTDLP_BIN` — explicit path to the yt-dlp binary (auto-detected from PATH otherwise)
   - `YTDLP_OUT` — default output directory (default: `~/Downloads/yt-dlp`)
4. **Install the skill**: copy this repo's contents into a Hermes skills directory (profile `skills/` folder) under the name `yt-dlp`.

## Harness

Every subcommand prints exactly one JSON object to stdout:

```json
{"ok": true, "code": 0, "cmd": ["..."], "files": ["C:/abs/path.mp4"], "info": ["..."], "out": "...", "err": "..."}
```

`files` is the final media file plus existing companions (`.info.json`, `.srt`, thumbnail); `info` is present only for the `info` command.

| Command | Purpose |
|---|---|
| `yt.py version` | yt-dlp version + ffmpeg/ffprobe/deno/node check |
| `yt.py info URL...` | metadata JSON per URL (title, duration, subs, formats) — no download |
| `yt.py formats URL` | format table |
| `yt.py subs URL` | manual + automatic caption tables |
| `yt.py download URL...` | video (mp4 by default) + info.json + English subs |
| `yt.py audio URL...` | audio extract (mp3 by default), metadata + thumbnail embedded |
| `yt.py clip URL --section SPEC...` | chapter names or time ranges, e.g. `"Intro"` `"01:20-02:00"` |
| `yt.py playlist URL [--items 1:5,8]` | playlist with `-I` spec + download archive (incremental re-runs) |
| `yt.py batch FILE` | batch file, one URL per line |
| `yt.py cookies export --browser B [--profile P] [--file PATH] [--all]` | dump browser cookies to a Netscape file (default: youtube.com+google.com domains only) |
| `yt.py cookies check FILE` | validate a Netscape cookies file (key YouTube cookies, expiry) |

Common options (any command): `--out DIR`, `--extra "RAW YT-DLP ARGS"` (repeatable — pass any raw flag the harness doesn't expose), `--timeout N` (default 1800 s), `--bin PATH`, `--cookies FILE`, `--cookies-from-browser BROWSER`, `--limit-rate 2M`, `--retries N`.

Download-family options: `--format mp4|mkv|webm|best` (video) / `mp3|m4a|wav|aac|opus|vorbis|flac|alac|best` (audio), `--no-subs`, `--subs "en.*,ja"`, `--no-info-json`, `--thumb`, `--sponsorblock "sponsor,intro"`. Playlist/batch: `--no-archive`.

### Examples

```bash
python scripts/yt.py info "https://www.youtube.com/watch?v=jNQXAC9IVRw"
python scripts/yt.py download "https://www.youtube.com/watch?v=jNQXAC9IVRw" --out ~/media
python scripts/yt.py audio "https://youtu.be/VIDEO_ID" --format m4a
python scripts/yt.py clip "https://youtu.be/VIDEO_ID" --section "Intro" "01:20-02:00"
python scripts/yt.py playlist "https://www.youtube.com/playlist?list=PL..." --items 1:5,8
python scripts/yt.py download "https://youtu.be/VIDEO_ID" --cookies ~/Downloads/yt-dlp/cookies.txt
python scripts/yt.py download "https://youtu.be/VIDEO_ID" --extra "-f best[height<=720]"
```

## Cookies (YouTube login)

- Export: `yt.py cookies export --browser chrome` — Chrome must be fully closed first (the harness detects a running Chrome and reports it). `--all` keeps every site; the default filters to youtube.com/google.com domains.
- Verify: `yt.py cookies check FILE` — reports the key session cookies (SAPISID, APISID, SID, HSID, SSID, YTLID, LOGIN_INFO, GOOGLE_SESS, HE) and their expiry.
- Use: `--cookies FILE` on any download command.
- Cookies unlock private / members-only / age-restricted content (account must be age-verified). They do NOT fix "Sign in to confirm you're not a bot" / 429s — those need fresh cookies (within ~30 min of a CAPTCHA), the same IP, and optionally the browser's User-Agent via `--extra "--add-headers \"User-Agent: ...\""`.
- Chrome 127+ (Windows) uses app-bound encryption: direct extraction can fail even with Chrome closed. Fallbacks: the "Get cookies.txt LOCALLY" browser extension, or Firefox (reads while open, plaintext DB).
- Alternative without cookies: YouTube supports direct login — `--extra "--username USER --password PASS"` (add `-2 CODE` for 2FA).
- Cookies files are full session tokens — treat them as secrets.

## Defaults baked into the harness

- download: mp4 (native mp4 video+audio preferred, merged fallback) + `.info.json` + English subtitles (manual + auto) as `.srt`
- audio: mp3, best VBR (`--audio-quality 0`), thumbnail + metadata embedded
- always: `--ignore-config --no-update --no-progress --newline -q --no-simulate`, Windows filename sanitization, titles trimmed to 120 bytes

## TODO

- **Linux version** (skill is currently Windows-only): install the release binary (`yt-dlp`, zipimport, needs Python 3.11+) or pip; verify `cookies-from-browser` under Linux keyrings (gnomekeyring/kwallet/basictext — over SSH the keyring is often not unlocked, prefer `cookies.txt`); cookies files use LF newlines (CRLF = HTTP 400); re-run the smoke suite; widen the `platforms` frontmatter and move Windows-specific environment facts into per-host notes. `scripts/yt.py` is already cross-platform — the Windows-specific parts live in the SKILL.md Environment section, the `--windows-filenames` default, and the `taskkill` hint.

## Smoke tests used to verify

`version`, `info`, `formats`, `subs`, `download` (mp4 + info.json + en.srt), `audio` (mp3 with embedded thumbnail), `cookies check`, `cookies export` (running-Chrome detection) — all against YouTube, ffprobe-verified output.

## License

MIT — see [LICENSE](LICENSE). yt-dlp itself is Unlicense; this repo contains no yt-dlp code.
