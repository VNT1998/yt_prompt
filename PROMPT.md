# Master Prompt Suite for YouTube Playlist Transcript Scraper

This document contains production-ready prompts designed for AI coding assistants, autonomous browser agents, and web automation tools to scrape transcripts from any YouTube Playlist with exact folder structures, line-separated formatting, resume capability, and rate-limit handling.

---

## 🎯 Master Prompt 1: AI Assistant & Code Generation Prompt
*(Use this prompt with ChatGPT, Claude, Antigravity, Cursor, or any AI coding assistant to build or run the scraping pipeline.)*

```markdown
Role: You are an expert Web Scraping and Automation Engineer.
Goal: Build a resilient automated scraper that extracts transcripts for all videos in a given YouTube Playlist.

### Strict File System & Formatting Requirements:
1. Base Directory:
   - ALWAYS create the base output directory (e.g. `transcripts/` or `output/`) first if it does not already exist.
2. Subfolder Structure:
   - Inside the base output directory, create a subfolder dynamically named after the Playlist Title (e.g. `transcripts/<playlist_name>/`).
3. File Naming Convention (Order Number Prefix):
   - Every exported file must start with a zero-padded order number prefix matching its position in the playlist:
     Format: `{order:0{pad_width}d}_{sanitized_video_title}_{video_id}.{ext}`
     Examples:
     - `001_What_is_Machine_Learning_ZftI2fEz0Fw.txt`
     - `047_Principle_Component_Analysis_iRbsBi5W0-c.txt`
4. Content Formatting (Line-by-Line Separation):
   - The transcript content MUST be separated line-by-line (each timestamp segment on its own distinct line).
   - DO NOT join or collapse the transcript into a single continuous line of text.

### Resiliency, Resume Mode & Anti-Ban Architecture:
1. Automatic Resume:
   - Before scraping video `N`, check if a valid file matching the order prefix and video ID already exists in the target subfolder.
   - If the file exists (>50 bytes), skip it and resume from the next missing video.
   - Provide a `--start-from <N>` and `--force` parameter.
2. Anti-Ban Rate Limiting & Delays:
   - Insert a polite randomized delay (default: 2–4 seconds) between requests.
3. Exponential Backoff on HTTP 429 / IP Blocks:
   - When YouTube returns `429 Too Many Requests`, `IpBlocked`, or `RequestBlocked`:
     - Do NOT terminate or crash.
     - Implement exponential backoff: sleep 15s -> 30s -> 60s -> 120s with progress logging.
     - Retry fetching up to 4 times before marking video as unavailable.
4. Optional Proxy & Cookies Support:
   - Allow passing `--proxy <url>` and `--cookies <file>` for cloud environments.

### Workflow & Technical Execution:
1. Playlist Parsing:
   - Extract the playlist title and ordered video list using `yt-dlp` or browser DOM.
2. Video Transcript Scraping:
   - Query auto-generated and manual transcripts in preferred languages: `['hi', 'hi-orig', 'en', 'en-US', 'en-GB', 'mr', ...]`.
   - Save line-separated output (`.txt`, `.md`, or `.json`) to the playlist subfolder.
```

---

## 🤖 Master Prompt 2: Autonomous Browser Agent Prompt
*(Use this prompt with Browser-Use, ChatGPT Operator, Claude Computer Use, or Playwright Browser Agents.)*

```markdown
Task: Scrape transcripts for all videos in YouTube Playlist: {{PLAYLIST_URL}}

Rules & Requirements:
1. Setup Output Hierarchy:
   - Create base directory `transcripts/` if not present.
   - Extract the Playlist Title from the page header (`#title`).
   - Create subfolder: `transcripts/<playlist_title>/`.
2. Resume Check:
   - Check existing files in `transcripts/<playlist_title>/`.
   - If `{{ORDER_NUM}}_{{TITLE}}.txt` exists, skip navigation and proceed to next video.
3. Process Each Video Sequentially:
   - Navigate to video #`{N}`.
   - Look for `button[aria-label="Show transcript"]`. If not visible, click description `#description-inline-expander`.
   - Click `button[aria-label="Show transcript"]`.
   - Wait for `ytd-engagement-panel-section-list-renderer[target-id="PAmodern_transcript_view"]`.
   - Extract all `transcript-segment-view-model` items:
     - Timestamp: `.ytwTranscriptSegmentViewModelTimestamp`
     - Text: `span.ytAttributedStringHost`
     - Chapter header (if present): `h3.ytwTimelineChapterViewModelTitle`
   - Save to `transcripts/<playlist_title>/{{ORDER_NUM}}_{{VIDEO_TITLE}}.txt` with explicit newlines between segments.
   - Wait 2–3 seconds before navigating to the next video to avoid rate limiting.
```

---

## 🔍 DOM Selector Reference Table

| UI Element | Modern Selector (2024–2026) | Fallback / Alternative |
| :--- | :--- | :--- |
| **Description Expander** | `#description-inline-expander #expand` | `tp-yt-paper-button#expand`, `#expand` |
| **"Show transcript" Button** | `button[aria-label="Show transcript"]` | `button:has-text("Show transcript")` |
| **Transcript Panel** | `ytd-engagement-panel-section-list-renderer[target-id="PAmodern_transcript_view"]` | `div#panels ytd-engagement-panel-section-list-renderer[visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED"]` |
| **Chapter Title** | `h3.ytwTimelineChapterViewModelTitle` | `.ytwTimelineChapterViewModelTitle` |
| **Transcript Segment** | `transcript-segment-view-model` | `.ytwTranscriptSegmentViewModelHost`, `ytd-transcript-segment-renderer` |
| **Timestamp** | `.ytwTranscriptSegmentViewModelTimestamp` | `.segment-timestamp` |
| **Transcript Text** | `span.ytAttributedStringHost` | `.segment-text`, `span[role="text"]` |
