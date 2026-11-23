#!/usr/bin/env python3
"""yt-dlp harness for Hermes.

Wraps yt-dlp with subcommands and prints exactly ONE JSON object to stdout:
  {"ok": bool, "code": int, "cmd": [...], "files": [paths...],
   "info": [...] (info command only), "out": "...", "err": "..."}

Subcommands:
  version     yt-dlp --version + dependency check
  info        metadata JSON per URL (-J), no download
  formats     format table for a URL
  subs        manual subtitles + automatic captions tables
  download    best mp4 video (+ info.json + en subs .srt by default)
  audio       audio extract (mp3 default; --format m4a|wav|aac|opus|vorbis|flac|alac|best)
  clip        --download-sections SPEC...  (chapter names or "01:20-02:00" ranges)
  playlist    -I item spec + download archive (incremental re-runs)
  batch       -a batch file (one URL per line)
  cookies     export (from browser to Netscape file) / check (validate a file)

Global options: --out DIR, --extra "RAW YT-DLP ARGS" (repeatable), --timeout N,
  --bin PATH, --cookies FILE, --cookies-from-browser BROWSER, --limit-rate R, --retries N

Env: YTDLP_BIN (binary), YTDLP_OUT (default output dir).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

FALLBACK_BIN = r"C:\Users\14843\bin\yt-dlp.exe"
COMPANION_EXTS = (".info.json", ".srt", ".vtt", ".jpg", ".webp", ".png")

VIDEO_FORMATS = {
    "mp4": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
    "mkv": "bv*[ext=mkv]+ba[ext=webm]/b[ext=mkv]/bv*+ba/b",
    "webm": "bv*[ext=webm]+ba[ext=webm]/b[ext=webm]/bv*+ba/b",
    "best": "bv*+ba/b",
}
AUDIO_FORMATS = ["mp3", "m4a", "wav", "aac", "opus", "vorbis", "flac", "alac", "best"]
DEFAULT_SUBS = "en"
KEY_YT_COOKIES = ["SAPISID", "APISID", "SID", "HSID", "SSID",
                  "YTLID", "LOGIN_INFO", "GOOGLE_SESS", "HE"]
YT_DOMAINS = ("youtube.com", "google.com")
BROWSER_PROCS = {
    "chrome": "chrome.exe", "chromium": "chrome.exe", "brave": "brave.exe",
    "edge": "msedge.exe", "opera": "opera.exe", "vivaldi": "vivaldi.exe",
    "whale": "whale.exe", "firefox": "firefox.exe", "safari": "Safari.exe",
}


def default_out():
    return os.environ.get("YTDLP_OUT") or os.path.join(
        os.path.expanduser("~"), "Downloads", "yt-dlp")


def find_bin(arg):
    for cand in (arg, os.environ.get("YTDLP_BIN")):
        if cand and os.path.isfile(cand):
            return cand
    for name in ("yt-dlp", "yt-dlp.exe"):
        p = shutil.which(name)
        if p:
            return p
    return FALLBACK_BIN


def run(bin_path, args, cwd, timeout):
    try:
        p = subprocess.run([bin_path] + args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=cwd,
                           timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError:
        return 127, "", "binary not found: %s" % bin_path
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err = (e.stderr or "") if isinstance(e.stderr, str) else ""
        return 124, out, "timeout after %ss: %s" % (timeout, err[-1000:])


def collect_files(out, cwd):
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        base = os.path.basename(line)
        if ("." in base) and base[0] != "." and " " not in base[:2]:
            path = line if os.path.isabs(line) else os.path.join(cwd, line)
            path = os.path.abspath(path)
            if os.path.exists(path):
                files.append(path)
    full = []
    for f in files:
        full.append(f)
        stem, _ = os.path.splitext(f)
        for ext in COMPANION_EXTS:
            c = stem + ext
            if os.path.exists(c) and c not in full:
                full.append(c)
    return full


def emit(code, out, err, cmd, files, info=None, extra=None):
    res = {"ok": code == 0, "code": code, "cmd": cmd, "files": files,
           "out": out[:30000], "err": err[-2000:]}
    if info is not None:
        res["info"] = info
    if extra:
        res.update(extra)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if code == 0 else 1


def browser_running(browser):
    exe = BROWSER_PROCS.get(browser)
    if not exe or os.name != "nt":
        return None
    try:
        p = subprocess.run(["tasklist", "/FI", "IMAGENAME eq %s" % exe,
                            "/NH"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        return exe.lower() in (p.stdout or "").lower()
    except Exception:
        return None


def base_args(ap, outdir, want_files):
    a = ["--ignore-config", "--no-update", "--no-progress", "--newline", "-q"]
    if os.name == "nt":
        a.append("--windows-filenames")
    if want_files:
        a.append("--no-simulate")
        a += ["-P", outdir, "-o", "%(title).120B [%(id)s].%(ext)s",
              "--print", "after_move:%(filepath)s"]
    if ap.limit_rate:
        a += ["--limit-rate", ap.limit_rate]
    if ap.retries:
        a += ["--retries", ap.retries]
    if ap.cookies:
        a += ["--cookies", ap.cookies]
    if ap.cookies_from_browser:
        a += ["--cookies-from-browser", ap.cookies_from_browser]
    a += ap.extra
    return a


def video_extra(a, ap):
    a += ["-f", VIDEO_FORMATS[ap.format], "-S", "res,fps,vcodec,acodec"]
    if not ap.no_subs:
        a += ["--write-subs", "--write-auto-subs", "--sub-langs", ap.subs,
              "--convert-subs", "srt"]
    if ap.info_json:
        a.append("--write-info-json")
    if ap.thumb:
        a.append("--write-thumbnail")
    if ap.sponsorblock:
        a += ["--sponsorblock-remove", ap.sponsorblock]


def common(sp):
    sp.add_argument("--out", default=None, help="output dir (default %s)" % default_out())
    sp.add_argument("--extra", action="append", default=[],
                    help="raw yt-dlp args, repeatable, e.g. --extra '-f best[height<=720]'")
    sp.add_argument("--bin", dest="bin_path", default=None, help="path to yt-dlp binary")
    sp.add_argument("--timeout", type=int, default=1800, help="max seconds (default 1800)")
    sp.add_argument("--cookies", default=None)
    sp.add_argument("--cookies-from-browser", dest="cookies_from_browser", default=None)
    sp.add_argument("--limit-rate", default=None, help="e.g. 2M")
    sp.add_argument("--retries", default=None)


def download_flags(sp):
    common(sp)
    sp.add_argument("--format", default="mp4", choices=list(VIDEO_FORMATS))
    sp.add_argument("--no-subs", action="store_true")
    sp.add_argument("--subs", default=DEFAULT_SUBS,
                    help="subtitle langs (regex), default %s" % DEFAULT_SUBS)
    sp.add_argument("--no-info-json", dest="info_json", action="store_false")
    sp.add_argument("--thumb", action="store_true")
    sp.add_argument("--sponsorblock", default=None,
                    help="categories to remove, e.g. 'sponsor,intro'")


def parse_netscape(path):
    cookies, header_ok, bad = [], False, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                if "cookie" in line.lower():
                    header_ok = True
                continue
            parts = line.split("\t")
            if len(parts) != 7:
                bad += 1
                continue
            domain, flag, cpath, secure, expiry, name, value = parts
            exp = None if expiry.strip() in ("", "0") else int(float(expiry))
            cookies.append({"domain": domain, "name": name, "value_len": len(value),
                            "secure": secure, "expires": exp,
                            "expired": exp is not None and exp < time.time()})
    return cookies, header_ok, bad


def filter_netscape(src, domains, dst):
    kept, dropped, header_ok = 0, 0, False
    with open(src, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    out_lines = []
    for line in lines:
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            if "cookie" in line.lower():
                header_ok = True
            out_lines.append(line)
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            out_lines.append(line)
            kept += 1
            continue
        domain = parts[0].lstrip(".").lower()
        if any(domain == d or domain.endswith("." + d) for d in domains):
            out_lines.append(line)
            kept += 1
        else:
            dropped += 1
    with open(dst, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\r\n".join(out_lines) + "\r\n")
    return kept, dropped, header_ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("version", help="version + dependency check")
    common(sp)

    sp = sub.add_parser("info", help="metadata JSON per URL, no download")
    common(sp)
    sp.add_argument("urls", nargs="+")

    sp = sub.add_parser("formats", help="format table")
    common(sp)
    sp.add_argument("url")

    sp = sub.add_parser("subs", help="subtitles + auto captions tables")
    common(sp)
    sp.add_argument("url")

    sp = sub.add_parser("download", help="video download (mp4 default)")
    download_flags(sp)
    sp.add_argument("urls", nargs="+")

    sp = sub.add_parser("audio", help="audio extract (mp3 default)")
    common(sp)
    sp.add_argument("--format", default="mp3", choices=AUDIO_FORMATS)
    sp.add_argument("--no-info-json", dest="info_json", action="store_false")
    sp.add_argument("urls", nargs="+")

    sp = sub.add_parser("clip", help="download sections/chapters")
    common(sp)
    sp.add_argument("--format", default="mp4", choices=list(VIDEO_FORMATS))
    sp.add_argument("--no-info-json", dest="info_json", action="store_false")
    sp.add_argument("--section", dest="sections", action="append", required=True,
                    help="chapter name or time range, repeatable, e.g. 'Intro' '01:20-02:00'")
    sp.add_argument("url")

    sp = sub.add_parser("playlist", help="playlist with -I items + archive")
    download_flags(sp)
    sp.add_argument("--items", default=None, help="-I item spec, e.g. '1:5,8' (default: all)")
    sp.add_argument("--no-archive", action="store_true")
    sp.add_argument("url")

    sp = sub.add_parser("batch", help="batch file, one URL per line")
    download_flags(sp)
    sp.add_argument("--no-archive", action="store_true")
    sp.add_argument("file")

    sp = sub.add_parser("cookies", help="export from browser / check a file")
    common(sp)
    csub = sp.add_subparsers(dest="cookies_cmd", required=True)
    cexp = csub.add_parser("export", help="dump browser cookies to a Netscape file")
    common(cexp)
    cexp.add_argument("--browser", required=True,
                      choices=["chrome", "chromium", "edge", "brave", "opera",
                               "vivaldi", "whale", "firefox", "safari"])
    cexp.add_argument("--profile", default=None, help="profile name or path")
    cexp.add_argument("--file", default=None, help="output cookies file")
    cexp.add_argument("--all", action="store_true",
                      help="keep cookies for all sites (default: youtube.com+google.com only)")
    cchk = csub.add_parser("check", help="validate a Netscape cookies file")
    common(cchk)
    cchk.add_argument("file")

    ap2 = ap.parse_args()
    bin_path = find_bin(getattr(ap2, "bin_path", None))
    outdir = ap2.out or default_out()
    os.makedirs(outdir, exist_ok=True)

    if ap2.cmd == "version":
        code, out, err = run(bin_path, ["--version"], outdir, ap2.timeout)
        deps = {n: shutil.which(n) for n in ("ffmpeg", "ffprobe", "deno", "node")}
        return emit(code, out.strip(), err, [bin_path, "--version"], [],
                    extra={"deps": deps, "bin": bin_path})

    if ap2.cmd == "info":
        args = ["--ignore-config", "--no-update", "-J"] + ap2.extra + ap2.urls
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        info, raw = [], []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                info.append(json.loads(line))
            except ValueError:
                raw.append(line)
        return emit(code, out, err, [bin_path] + args, [], info=info,
                    extra={"info_unparsed": raw} if raw else None)

    if ap2.cmd == "formats":
        args = ["--ignore-config", "--no-update", "--print", "formats_table"] + ap2.extra + [ap2.url]
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, [])

    if ap2.cmd == "subs":
        args = ["--ignore-config", "--no-update",
                "--print", "subtitles_table", "--print", "automatic_captions_table",
                ] + ap2.extra + [ap2.url]
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, [])

    if ap2.cmd == "download":
        args = base_args(ap2, outdir, True)
        video_extra(args, ap2)
        args += ap2.urls
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, collect_files(out, outdir))

    if ap2.cmd == "audio":
        args = base_args(ap2, outdir, True)
        args += ["-f", "ba/b", "-x", "--audio-format", ap2.format,
                 "--audio-quality", "0", "--embed-thumbnail", "--embed-metadata"]
        if ap2.info_json:
            args.append("--write-info-json")
        args += ap2.urls
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, collect_files(out, outdir))

    if ap2.cmd == "clip":
        args = base_args(ap2, outdir, True)
        args += ["-f", VIDEO_FORMATS[ap2.format], "-S", "res,fps,vcodec,acodec"]
        for s in ap2.sections:
            args += ["--download-sections", s]
        if ap2.info_json:
            args.append("--write-info-json")
        args.append(ap2.url)
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, collect_files(out, outdir))

    if ap2.cmd == "playlist":
        args = base_args(ap2, outdir, True)
        video_extra(args, ap2)
        if ap2.items:
            args += ["-I", ap2.items]
        if not ap2.no_archive:
            args += ["--download-archive",
                     os.path.join(outdir, "yt-dlp-archive.txt")]
        args.append(ap2.url)
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, collect_files(out, outdir))

    if ap2.cmd == "batch":
        args = base_args(ap2, outdir, True)
        video_extra(args, ap2)
        if not ap2.no_archive:
            args += ["--download-archive",
                     os.path.join(outdir, "yt-dlp-archive.txt")]
        args += ["-a", ap2.file]
        code, out, err = run(bin_path, args, outdir, ap2.timeout)
        return emit(code, out, err, [bin_path] + args, collect_files(out, outdir))

    if ap2.cmd == "cookies":
        if ap2.cookies_cmd == "export":
            spec = ap2.browser + ((":" + ap2.profile) if ap2.profile else "")
            out_file = os.path.abspath(ap2.file or os.path.join(outdir, "cookies.txt"))
            running = browser_running(ap2.browser)
            args = ["--ignore-config", "--no-update", "-q",
                    "--cookies-from-browser", spec, "--cookies", out_file]
            code, out, err = run(bin_path, args, outdir, ap2.timeout)
            extra = {}
            if running is not None:
                extra["browser_running"] = running
                if running:
                    extra["hint"] = ("close the browser first (e.g. taskkill /IM %s /F) "
                                     "or export with the 'Get cookies.txt LOCALLY' extension"
                                     % BROWSER_PROCS.get(ap2.browser, "<browser>.exe"))
            if os.path.isfile(out_file):
                if not ap2.all:
                    kept, dropped, header_ok = filter_netscape(out_file, YT_DOMAINS, out_file)
                    extra["kept"] = kept
                    extra["dropped_other_sites"] = dropped
                    extra["header_ok"] = header_ok
                else:
                    _, header_ok, _ = parse_netscape(out_file)
                    extra["header_ok"] = header_ok
                cookies, _, _ = parse_netscape(out_file)
                extra["cookie_count"] = len(cookies)
            else:
                extra["cookie_count"] = 0
            ok = os.path.isfile(out_file) and os.path.getsize(out_file) > 0
            extra["file"] = out_file
            return emit(0 if ok else 1, out, err, [bin_path] + args, [] if not ok else [out_file],
                        extra=extra)
        else:  # check
            f = ap2.file
            if not os.path.isfile(f):
                return emit(1, "", "file not found: %s" % f, [], [],
                            extra={"file": os.path.abspath(f)})
            cookies, header_ok, bad = parse_netscape(f)
            now = time.time()
            key = {name: "missing" for name in KEY_YT_COOKIES}
            for c in cookies:
                if c["name"] in key:
                    key[c["name"]] = "expired" if c["expired"] else "ok"
            domains = sorted({c["domain"] for c in cookies})
            expired = [c["name"] for c in cookies if c["expired"]]
            expiring = [c["name"] for c in cookies
                        if c["expires"] is not None and 0 < c["expires"] - now < 7 * 86400]
            ok = header_ok and bad == 0 and len(cookies) > 0
            return emit(0 if ok else 1, "", "bad lines: %d" % bad if bad else "",
                        [], [], extra={"file": os.path.abspath(f), "header_ok": header_ok,
                                       "cookie_count": len(cookies), "key_cookies": key,
                                       "expired": expired, "expiring_soon": expiring,
                                       "domains": domains[:40]})


if __name__ == "__main__":
    sys.exit(main())
