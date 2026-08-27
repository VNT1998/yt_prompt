"""
URL and Metadata Parsing Utilities
"""

import re
import json
import subprocess
import urllib.request
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from .constants import DEFAULT_USER_AGENT


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract 11-character YouTube video ID from various URL formats."""
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith(("/embed/", "/v/", "/shorts/")):
            parts = parsed.path.split("/")
            return parts[2] if len(parts) > 2 else None
    elif parsed.hostname == "youtu.be":
        return parsed.path[1:].split("?")[0]

    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_or_id)
    return match.group(1) if match else None


def extract_playlist_id(url_or_id: str) -> Optional[str]:
    """Extract playlist ID from a URL or raw string."""
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if url_or_id.startswith(("PL", "UU", "FL", "RD", "OLAK5uy_")):
        return url_or_id
    parsed = urlparse(url_or_id)
    query = parse_qs(parsed.query)
    return query.get("list", [None])[0]


def fetch_video_title(video_id: str) -> str:
    """Fetch video title using YouTube oEmbed without requiring an API key."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("title", f"video_{video_id}")
    except Exception:
        return f"video_{video_id}"


def sanitize_filename(name: str) -> str:
    """Clean string to make it safe for directory and file names."""
    if not name:
        return "untitled"
    # Remove filesystem illegal characters
    cleaned = re.sub(r'[\\/*?:"<>|#%&{}\\<>*?/$!\'":@+`|=]', "", name)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned[:80] if cleaned else "untitled"


def fetch_playlist_metadata(playlist_url: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract playlist title and ordered list of video metadata using yt-dlp.
    """
    cmd = ["yt-dlp", "--flat-playlist", "--dump-single-json", playlist_url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        playlist_title = data.get("title") or "YouTube_Playlist"
        raw_entries = data.get("entries") or []

        videos = []
        for entry in raw_entries:
            if not entry:
                continue
            v_id = entry.get("id") or extract_video_id(entry.get("url", ""))
            v_title = entry.get("title") or fetch_video_title(v_id)
            v_url = (
                entry.get("url")
                if (entry.get("url") and str(entry.get("url")).startswith("http"))
                else f"https://www.youtube.com/watch?v={v_id}"
            )
            if v_id:
                videos.append(
                    {
                        "id": v_id,
                        "title": v_title,
                        "url": v_url,
                        "duration": entry.get("duration"),
                    }
                )
        return playlist_title, videos
    except Exception as e:
        # Fallback to line-by-line streaming
        try:
            cmd2 = ["yt-dlp", "--flat-playlist", "--dump-json", playlist_url]
            res2 = subprocess.run(cmd2, capture_output=True, text=True, check=True)
            videos = []
            for line in res2.stdout.strip().split("\n"):
                if not line:
                    continue
                d = json.loads(line)
                v_id = d.get("id") or extract_video_id(d.get("url", ""))
                v_title = d.get("title") or fetch_video_title(v_id)
                v_url = (
                    d.get("url")
                    if (d.get("url") and str(d.get("url")).startswith("http"))
                    else f"https://www.youtube.com/watch?v={v_id}"
                )
                if v_id:
                    videos.append(
                        {
                            "id": v_id,
                            "title": v_title,
                            "url": v_url,
                            "duration": d.get("duration"),
                        }
                    )
            p_id = extract_playlist_id(playlist_url) or "playlist"
            return f"playlist_{p_id}", videos
        except Exception:
            return "YouTube_Playlist", []
