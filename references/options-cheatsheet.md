# yt-dlp Options Cheatsheet (v2026.10.26)

Condensed from the yt-dlp README for the harness skill. Use raw flags via `yt.py ... --extra "FLAG ..."` when a task needs something the harness doesn't expose.

Invocation: `yt-dlp [OPTIONS] [--] URL [URL...]`

## Option groups (key flags)

- General: `-i/--ignore-errors`, `--abort-on-error`, `--list-extractors`, `--use-extractors/--ies "holodex.*,end,youtube"` (prefix `-` to exclude), `--default-search "gvsearch2:term"` (auto/error/fixup_error), `--ignore-config`, `--flat-playlist`, `--live-from-start`, `--wait-for-video MIN[-MAX]`, `--mark-watched`, `--preset-alias mp3|aac|mp4|mkv|sleep`, `--alias NAME "options"`, `--js-runtimes deno|node|quickjs|bun`
- Network: `--proxy socks5://...`, `--socket-timeout N`, `--source-address IP`, `--impersonate chrome[:os]` (curl_cffi), `--list-impersonate-targets`, `-4/-6`
- Geo: `--geo-verification-proxy URL`, `--xff default|never|CC|CIDR`
- Video Selection: `-I 1:3,7,-5::2` (playlist items; negative step = reverse), `--min-filesize/--max-filesize 50M`, `--date/--datebefore/--dateafter today-2weeks`, `--match-filters "view_count>?100 & description~='(?i)cats'"`, `--break-match-filters`, `--no-playlist/--yes-playlist`, `--age-limit N`, `--download-archive FILE`, `--max-downloads N`, `--break-on-existing`, `--skip-playlist-after-errors N`
- Download: `-N 4` (concurrent fragments), `-r/--limit-rate 50K`, `--throttled-rate 100K`, `-R/--retries 10|infinite`, `--retry-sleep linear=1::2`, `--skip-unavailable-fragments`, `--keep-fragments`, `--buffer-size 16K`, `--http-chunk-size 10M`, `--playlist-random`, `--lazy-playlist`, `--download-sections "*10:15-inf"|"chapter"|"*from-url"` (multiple allowed; `*` = time range, needs ffmpeg), `--downloader [proto:]name` (aria2c, curl, wget, ffmpeg, native, httpie, axel), `--downloader-args name:args`
- Filesystem: `-a FILE` (batch; `#`/`;`/`]` comment lines), `-P [type:]PATH` (also `home:`/`temp:`), `-o [type:]TEMPLATE`, `--output-na-placeholder X` (default NA), `--restrict-filenames`, `--windows-filenames`, `--trim-filenames N`, `-w/--no-overwrites`, `--force-overwrites`, `-c/--continue` (default), `--mtime`, `--write-description`, `--write-info-json`, `--write-comments`, `--load-info-json FILE` (re-download from saved metadata), `--cookies FILE`, `--cookies-from-browser chrome[:profile]`, `--cache-dir DIR`
- Thumbnails: `--write-thumbnail`, `--write-all-thumbnails`
- Verbosity/Simulation: `-q`, `--no-warnings`, `-s/--simulate`, `--skip-download`, `-O/--print [WHEN:]TEMPLATE` (implies simulate unless --no-simulate), `--print-to-file [WHEN:]TEMPLATE FILE`, `-j/--dump-json` (per entry), `-J/--dump-single-json` (one line per URL/playlist), `--newline`, `--no-progress`, `-v/--verbose`, `--dump-pages`, `--print-traffic`
- Workarounds: `--add-headers "User-Agent: ..."`, `--sleep-requests N`, `--sleep-interval N --max-sleep-interval N`, `--no-check-certificates`

## Format selection (`-f`, `-S`)

Selectors: `22` (format id) · `webm` (best ext) · `b/best` (v+a) · `bv/bestvideo` (video-only) · `ba/bestaudio` (audio-only) · `bv*`/`ba*` (contains) · `best.2` (2nd best) · `22/17/18` (preference) · `22,17` (all, separate files) · `bv+ba` (merge; needs ffmpeg) · `all[...]` · groups: `(mp4,webm)[height<480]`.

Filters — numeric `< <= > >= = !=`: filesize, filesize_approx, width, height, aspect_ratio, tbr, abr, vbr, asr, fps, audio_channels, stretched_ratio. String `= ^= $= *= ~=` (+`!` negation): url, ext, acodec, vcodec, container, protocol, language, dynamic_range, format_id, format, format_note, resolution. Append `?` to an operator to include unknown values: `bv[height<=?720]`.

Sort fields (`-S f1,f2`, `+` to invert, `:value` to cap/prefer, `~` nearest): hasvid, hasaud, ie_pref, lang, quality, source, proto, vcodec (av01>vp9.2>vp9>h265>h264>vp8>...), acodec (flac/alac>wav>opus>vorbis>aac>mp4a>mp3>...), codec, vext (mp4>mov>webm>flv), aext (m4a>aac>mp3>ogg>opus>webm), ext, filesize, fs_approx, size, height, width, res, fps, hdr (DV>HDR12>HDR10+>HDR10>HLG>SDR; default hdr:12), channels, tbr, vbr, abr, br, asr. Default order: `lang,quality,res,fps,hdr:12,vcodec,channels,acodec,size,br,asr,proto,ext,hasaud,source,id` (hasvid+ie_pref always first unless `--format-sort-force`).

Useful examples:
- 720p or best-under: `-f "bv*[height<=720]+ba[height<=?720]/b[height<=720]"` (720p cap via sort: `-f bv*+ba -S "res:720,fps,vcodec,acodec"`)
- Smallest file: `-f best -S +size,+br,+res,+fps`
- Native mp4 (no remux): `-f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"`
- Remux anyway: `--merge-output-format mp4` (containers: avi,flv,mkv,mov,mp4,webm)
- `-v -F` shows the sort order (worst→best).

## Output template (`-o`)

Syntax: `%(name[.keys][arithmetic][>strf][,alt][&repl][|default])[flags][width][.prec][len]type`. Types: standard printf + `B` bytes, `j` json, `h` html-escape, `l` list, `q` shell-quote, `D` decimal suffix, `S` sanitize-filename, `U` unicode-normalize. Per-type templates: `-o "subtitle:%(title)s.%(ext)s"` (types: subtitle, thumbnail, description, infojson, link, pl_* , chapter, pl_video; empty template = skip that type).

Key fields: id, title, fulltitle, ext, alt_title, description, uploader(_id/_url), license, timestamp, upload_date, release_date, duration, duration_string, view_count, like_count, is_live, live_status, availability, start_time, end_time, extractor(_key), epoch, autonumber, n_entries, playlist_id/title/index/webpage_url, webpage_url(_domain/_basename), categories, tags, chapter(_number/_id), series/season/episode(_number), track/album/artist(s)/genre(s), section_title/number/start/end (clips), urls + filename + formats_table + subtitles_table + automatic_captions_table + thumbnails_table (only in --print), filepath (only after download/post-processing).

Examples: `%(uploader).30B - %(title).200B.%(ext)s` (byte-trim) · `%(upload_date>%Y-%m-%d)s` (strftime) · `%(uploader|Unknown)s` (default) · `%(release_date>%Y,upload_date>%Y|Unknown)s` (alternate).

## `--print` WHEN values

pre_process, post_process, pre_video, post_video, after_move, before_dl, after_dl, after_video, before_move, end, start (default `video`). `--print after_move:%(filepath)s` = final path after all post-processing. `--print "%()j"` = whole infodict as JSON (old `-j` equivalent).

## Subtitles

`--write-subs`, `--write-auto-subs`, `--sub-langs "en.*,ja"` (regex per lang; `-` to exclude; `all`), `--sub-format srt` or `ass/srt/best`, `--convert-subs srt`, `--list-subs` (= `--print subtitles_table --print automatic_captions_table`). Auto captions need the `auto/` prefix in langs.

## Post-processing

`-x/--extract-audio`, `--audio-format best|aac|alac|flac|m4a|mp3|opus|vorbis|wav`, `--audio-quality 0..10 (VBR) or 128K` (default 5), `--remux-video mp4` (or rules `aac>m4a/mov>mp4/mkv`), `--recode-video FORMAT`, `--postprocessor-args "Merger+ffmpeg_i1:-v quiet"` (alias --ppa), `-k/--keep-video`, `--embed-subs` (mp4/webm/mkv only), `--embed-thumbnail`, `--embed-metadata` (also embeds chapters/infojson), `--embed-chapters`, `--embed-info-json` (mkv/mka), `--split-chapters`.

## SponsorBlock

`--sponsorblock-mark CATS` (chapters), `--sponsorblock-remove CATS` (cut; needs ffmpeg). Categories: sponsor, intro, outro, selfpromo, preview, filler, interaction, music_offtopic, hook, poi_highlight, chapter, all, default (=all,-filler for remove).

## Preset aliases (exact expansions)

- `-t mp3`: `-f 'ba[acodec^=mp3]/ba/b' -x --audio-format mp3`
- `-t aac`: `-f 'ba[acodec^=aac]/ba[acodec^=mp4a.40.]/ba/b' -x --audio-format aac`
- `-t mp4`: `--merge-output-format mp4 --remux-video mp4 -S vcodec:h264,lang,quality,res,fps,hdr:12,aocodec:aac`
- `-t mkv`: `--merge-output-format mkv --remux-video mkv`
- `-t sleep`: `--sleep-subtitles 5 --sleep-requests 0.75 --sleep-interval 10 --max-sleep-interval 20`

## Authentication / cookies

`-u/-p/-2` (user/pass/2fa — YouTube supports username/password login directly), `-n/--netrc`, `--video-password`, `--cookies FILE` (Netscape format; first line `# Netscape HTTP Cookie File` or `# HTTP Cookie File`; CRLF on Windows, LF on Unix — wrong newlines = HTTP 400), `--cookies-from-browser BROWSER[+KEYRING][:PROFILE][::CONTAINER]` (chrome, chromium, edge, brave, opera, vivaldi, whale, firefox, safari; Chromium browsers must be closed — DB lock; Chrome 127+ Windows has app-bound encryption that can break extraction; Firefox reads while open and is plaintext). Export trick: `yt-dlp --cookies-from-browser chrome --cookies out.txt --skip-download URL` dumps the whole jar (ALL sites). Key YouTube session cookies: SAPISID, APISID, SID, HSID, SSID, YTLID, LOGIN_INFO, GOOGLE_SESS, HE.

## Extractor args

`--extractor-args IE_KEY:ARGS` (repeatable), `--extractor-retries N`, `--hls-split-discontinuity`, `--allow-dynamic-mpd`. Check a site's args: `yt-dlp --extractor-descriptions`.

## Updates

`yt-dlp -U` (same channel) · `--update-to nightly|stable|master` · `--update-to stable@2023.07.06` · `--update-to owner/repo@TAG`. Warnings for builds older than 90 days (suppress with `--no-update`).

## FAQ pitfalls

- Quote URLs in shells; in Windows .bat files double the `%` in `-o` templates.
- 429/402 = soft IP block → solve CAPTCHA in browser, pass fresh cookies (+ `--source-address` for the same IP).
- Cloudflare 403 → fresh browser cookies + the browser's full current User-Agent via `--add-headers`.
- File name too long → byte-trim the template (`%(title).200B`) or `--trim-filenames N`.
- Clips/sponsor cuts are keyframe-accurate only; `--force-keyframes-at-cuts` re-encodes (slow).
- `-o -` streams the video to stdout (relay for players on other machines); YouTube throttles HTTP chunk sizes > 10 MB.
- Standalone release binaries bundle: Python, certifi, brotli, websockets, requests, mutagen, pycryptodomex, secretstorage, curl_cffi (most builds).
