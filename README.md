# yt-scribe

YouTube transcript CLI tool. Fetches transcripts and saves them as structured Markdown with YAML frontmatter — searchable, git-trackable, and compatible with Obsidian, Hugo, Jekyll, etc.

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/verdey/yt-scribe.git
cd yt-scribe
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Single video

```bash
# Save as Markdown file
yt-scribe https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Print to stdout
yt-scribe dQw4w9WgXcQ --stdout

# JSON output
yt-scribe dQw4w9WgXcQ --json --stdout | jq '.segments[:3]'

# Spanish transcript (auto-fallback if unavailable)
yt-scribe dQw4w9WgXcQ --lang es

# Richer metadata via yt-dlp (upload date, description)
yt-scribe dQw4w9WgXcQ --enrich
```

### Search + bundle

Search YouTube, interactively select videos, and download transcripts into a named bundle:

```bash
yt-scribe search "python concurrency"
```

Non-interactive (JSON output for scripting):

```bash
yt-scribe search "python concurrency" -n 5 --json
```

### Playlist import

Import a public YouTube playlist as a bundle:

```bash
yt-scribe playlist "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
```

### Batch download

Download specific videos non-interactively:

```bash
yt-scribe batch dQw4w9WgXcQ xvFZjo5PgG0 --bundle my-research -o ~/transcripts
```

From a file (one URL/ID per line, `#` comments ignored):

```bash
yt-scribe batch --from-file urls.txt --bundle my-research
```

Streaming progress (JSONL, one event per line):

```bash
yt-scribe batch dQw4w9WgXcQ --bundle test --jsonl
```

### Bundle append

Downloading into an existing bundle automatically merges — the index is regenerated from all files on disk. No special flags needed:

```bash
yt-scribe batch VIDEO1 --bundle existing-bundle -o ~/transcripts
yt-scribe batch VIDEO2 --bundle existing-bundle -o ~/transcripts
# _index.md now lists both videos, original metadata preserved
```

## Output format

### Markdown (default)

```markdown
---
title: "How to Build a REST API with Python"
channel: "Fireship"
video_id: "z2YRzZbFg3g"
url: "https://www.youtube.com/watch?v=z2YRzZbFg3g"
duration: "12m 34s"
language: "English"
transcript_type: "auto-generated"
fetched_at: "2026-02-22 15:30:00 UTC"
---

# How to Build a REST API with Python

**Channel:** [Fireship](https://www.youtube.com/@Fireship)
**Duration:** 12m 34s
**Language:** English (auto-generated)

---

## Transcript

**[0:00]** in this video we're going to build a rest api from scratch

**[0:04]** using python and the flask framework
```

Filenames: `{Sanitized_Title}_{videoId}.md`

### JSON

```bash
yt-scribe dQw4w9WgXcQ --json --stdout
```

Returns video metadata + timestamped segments array.

## Web UI

A PHP + Alpine.js web interface lives in `web/`. It provides search, playlist import, bundle management, and streaming download progress via SSE.

Requires PHP 8.0+ (e.g., [Laravel Herd](https://herd.laravel.com/)):

```bash
cd web
php -S localhost:8080
```

## CLI reference

```
yt-scribe <video> [options]            Fetch a single transcript
yt-scribe search <query> [options]     Search YouTube + interactive select
yt-scribe playlist <url> [options]     Import a playlist
yt-scribe batch <videos...> [options]  Non-interactive batch download

Options (single video):
  -o, --output DIR       Output directory (default: ./transcripts/)
  -l, --lang LANG...     Preferred language(s) (default: en)
  --json                 Output JSON instead of Markdown
  --enrich               Use yt-dlp for richer metadata
  --stdout               Print to stdout instead of file
  -v, --verbose          Debug logging

Options (search):
  -n, --results N        Number of results (default: 10, max: 25)
  --bundle NAME          Bundle name (default: auto from query)
  --json                 Output results as JSON (non-interactive)

Options (playlist):
  --bundle NAME          Bundle name (default: auto from title)
  --json                 Output playlist info as JSON (non-interactive)

Options (batch):
  --bundle NAME          Bundle name (required)
  --from-file FILE       Read video IDs/URLs from file
  --json                 Output results as JSON
  --jsonl                Streaming JSON (one event per line)
```

## Dependencies

- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) — transcript fetching
- [requests](https://docs.python-requests.org/) — YouTube oEmbed metadata
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — enriched metadata + search/playlist

## License

MIT
