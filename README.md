# YouTube Playlist Transcript Scraper & Prompt Suite

A modular, production-ready tool and prompt suite to extract transcripts for all videos in a YouTube playlist with auto-resume, rate-limit protection, and clean line-by-line formatting.

---

## 🏗️ Project Structure

```text
yt_prompt/
├── .gitignore                     # Git ignore rules (ignores local transcripts & logs)
├── pyproject.toml                 # Packaging specification (PEP 518/PEP 621)
├── requirements.txt               # Dependencies list
├── README.md                      # Documentation & Quickstart
├── PROMPT.md                      # Master prompt engineering reference for AI agents
├── main.py                        # Top-level entry point
├── scraper.py                     # Convenience CLI wrapper
├── src/
│   └── yt_prompt/                 # Core Python package
│       ├── __init__.py            # Package exports
│       ├── cli.py                 # Command Line Interface (argparse)
│       ├── core.py                # Core scraper with auto-resume & backoff engine
│       ├── browser.py             # Playwright DOM interaction scraper
│       ├── parsers.py             # URL extraction, playlist metadata & sanitizers
│       ├── formatters.py          # Line-separated Markdown, TXT, and JSON formatters
│       └── constants.py           # Selectors, timeouts, and headers
├── scripts/
│   └── console_extractor.js       # 1-Click browser DevTools console script
└── tests/
    ├── __init__.py
    └── test_parsers.py            # Unit tests for URL and metadata parsing
```

---

## ✨ Features

- **Standardized Folder Organization**: Automatically creates `<output_dir>/<playlist_title>/`.
- **Ordered File Prefixing**: Formats filenames as `001_`, `002_`, ..., `134_` based on playlist position.
- **Line-by-Line Separation**: Transcripts are written with clear newlines per segment (never collapsed into a single line).
- **Auto-Resume Capability**: Detects existing downloaded transcripts and resumes from where it stopped.
- **Anti-Ban / Rate-Limit Protection**: Randomized delays between requests and exponential backoff retry on HTTP 429 errors.
- **Multi-Format Export**: Supports `.txt` (clean narrative), `.md` (timestamped bullets + chapters), and `.json` (structured array).
- **Proxy & Browser Modes**: Supports `--proxy` and `--browser` for headless DOM scraping.

---

## 🚀 Quickstart

### 1. Installation

```bash
git clone https://github.com/VNT1998/yt_prompt.git
cd yt_prompt
pip install -r requirements.txt
```

*(Optional for browser DOM mode)*:
```bash
pip install playwright && playwright install chromium
```

---

### 2. Usage Examples

```bash
# Scrape an entire playlist (with auto-resume and line-separated .txt output):
python3 main.py "https://youtube.com/playlist?list=PLKnIA16_Rmvbr7zKYQuBfsVkjoLcJgxHH" -o transcripts -f txt

# Export all formats (.md, .txt, .json) with a custom delay between requests:
python3 main.py "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID" -o transcripts -f all -d 3.0

# Resume explicitly from video #47 onwards:
python3 main.py "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID" -o transcripts -f txt -s 47

# Use Playwright Headless Browser DOM mode:
python3 main.py "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID" -o transcripts --browser
```

---

### 3. CLI Options Reference

| Argument | Flag | Default | Description |
| :--- | :--- | :--- | :--- |
| **URL** | `url` | *Required* | YouTube Playlist or Video URL |
| **Output Directory** | `-o`, `--output` | `transcripts` | Base output directory |
| **Format** | `-f`, `--format` | `txt` | Output format: `txt`, `md`, `json`, or `all` |
| **Delay** | `-d`, `--delay` | `2.0` | Delay in seconds between requests for rate limiting |
| **Start From** | `-s`, `--start-from` | `1` | Video index number to start/resume from |
| **Force Overwrite** | `--force` | `False` | Re-download files even if already existing |
| **Proxy** | `--proxy` | `None` | HTTP/HTTPS/SOCKS proxy URL |
| **Browser DOM** | `--browser` | `False` | Use Playwright DOM scraper instead of API |

---

### 4. Running Tests

```bash
PYTHONPATH=src python3 -m unittest discover tests
```
