"""
Core YouTube Transcript Scraper with Auto-Resume and Anti-Ban Engine
"""

import os
import time
import random
from typing import List, Dict, Any, Optional
from .constants import DEFAULT_LANGUAGES
from .parsers import (
    extract_video_id,
    extract_playlist_id,
    fetch_video_title,
    fetch_playlist_metadata,
    sanitize_filename,
)
from .formatters import (
    format_timestamp,
    is_video_already_downloaded,
    save_transcript,
)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig
    HAS_YTT = True
except ImportError:
    HAS_YTT = False
    YouTubeTranscriptApi = None


class PlaylistScraper:
    """
    Production-ready YouTube Playlist Transcript Scraper.
    """

    def __init__(
        self,
        output_dir: str = "transcripts",
        format_type: str = "txt",
        delay_seconds: float = 2.0,
        languages: List[str] = None,
        max_retries: int = 4,
        force_overwrite: bool = False,
        proxy_url: Optional[str] = None,
    ):
        self.output_dir = output_dir
        self.format_type = format_type
        self.delay_seconds = delay_seconds
        self.languages = languages or DEFAULT_LANGUAGES
        self.max_retries = max_retries
        self.force_overwrite = force_overwrite
        self.proxy_url = proxy_url

    def fetch_single_transcript(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch transcript via youtube-transcript-api with multi-language fallback."""
        if not HAS_YTT:
            raise RuntimeError("youtube-transcript-api is not installed.")

        proxy_config = (
            GenericProxyConfig(http_url=self.proxy_url, https_url=self.proxy_url)
            if self.proxy_url
            else None
        )
        ytt = YouTubeTranscriptApi(proxy_config=proxy_config)

        try:
            transcript_obj = ytt.fetch(video_id, languages=self.languages)
            raw_items = (
                transcript_obj.to_raw_data()
                if hasattr(transcript_obj, "to_raw_data")
                else list(transcript_obj)
            )
            return [
                {
                    "start": item.get("start") if isinstance(item, dict) else item.start,
                    "duration": (
                        item.get("duration") if isinstance(item, dict) else item.duration
                    ),
                    "timestamp": format_timestamp(
                        item.get("start") if isinstance(item, dict) else item.start
                    ),
                    "text": (
                        item.get("text") if isinstance(item, dict) else item.text
                    )
                    .replace("\n", " ")
                    .strip(),
                }
                for item in raw_items
            ]
        except Exception as e:
            err_msg = str(e).lower()
            if any(
                k in err_msg
                for k in ["429", "blocking requests", "ip", "too many requests"]
            ):
                raise e

            # Fallback: List available transcripts
            try:
                transcript_list = ytt.list(video_id)
                available = None
                for t in transcript_list:
                    available = t
                    break
                if available:
                    fetched = available.fetch()
                    return [
                        {
                            "start": (
                                item.get("start") if isinstance(item, dict) else item.start
                            ),
                            "duration": (
                                item.get("duration")
                                if isinstance(item, dict)
                                else item.duration
                            ),
                            "timestamp": format_timestamp(
                                item.get("start") if isinstance(item, dict) else item.start
                            ),
                            "text": (
                                item.get("text") if isinstance(item, dict) else item.text
                            )
                            .replace("\n", " ")
                            .strip(),
                        }
                        for item in fetched
                    ]
            except Exception as inner_e:
                inner_msg = str(inner_e).lower()
                if any(k in inner_msg for k in ["429", "blocking requests", "ip"]):
                    raise inner_e
                return None
        return None

    def fetch_with_backoff(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch transcript with exponential backoff on HTTP 429."""
        for attempt in range(1, self.max_retries + 1):
            try:
                return self.fetch_single_transcript(video_id)
            except Exception as e:
                err_str = str(e).lower()
                if any(
                    k in err_str
                    for k in [
                        "429",
                        "blocking requests",
                        "too many requests",
                        "ipblocked",
                        "requestblocked",
                    ]
                ):
                    wait_seconds = 15 * (2 ** (attempt - 1)) + random.uniform(1.0, 4.0)
                    print(
                        f"[!] Rate Limit (429) on video {video_id}! "
                        f"Cooling down for {wait_seconds:.1f}s (Attempt {attempt}/{self.max_retries})..."
                    )
                    time.sleep(wait_seconds)
                else:
                    return None
        return None

    def scrape(self, url: str, start_from: int = 1) -> Dict[str, Any]:
        """
        Scrapes all transcripts for a given playlist or single video.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        v_id = extract_video_id(url)
        p_id = extract_playlist_id(url)

        playlist_title = "Single_Videos"
        videos = []

        if "list=" in url or p_id:
            print(f"[*] Discovering videos in playlist: {url}")
            playlist_title, videos = fetch_playlist_metadata(url)
            print(f"[*] Playlist Title: '{playlist_title}' ({len(videos)} videos)")
        elif v_id:
            title = fetch_video_title(v_id)
            print(f"[*] Processing single video: '{title}' (ID: {v_id})")
            videos = [
                {
                    "id": v_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={v_id}",
                }
            ]

        if not videos:
            print("[!] No videos found.")
            return {"total": 0, "success": 0, "skipped": 0, "failed": 0}

        safe_subfolder = sanitize_filename(playlist_title)
        target_dir = os.path.join(self.output_dir, safe_subfolder)
        os.makedirs(target_dir, exist_ok=True)

        total_videos = len(videos)
        pad_width = max(2, len(str(total_videos)))
        success_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, video in enumerate(videos, start=1):
            if idx < start_from:
                skipped_count += 1
                continue

            order_prefix = f"{idx:0{pad_width}d}"
            v_title = video.get("title", f"video_{idx}")
            curr_id = video.get("id", "")

            # Resume Check
            if not self.force_overwrite and is_video_already_downloaded(
                target_dir, order_prefix, curr_id, self.format_type
            ):
                print(f"[⏩ Resumed] [{idx}/{total_videos}] #{order_prefix} '{v_title}' exists. Skipping.")
                skipped_count += 1
                continue

            print(f"\n--- [{idx}/{total_videos}] Fetching: #{order_prefix} {v_title} ({curr_id}) ---")

            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds + random.uniform(0.5, 1.5))

            segments = self.fetch_with_backoff(curr_id)
            if segments:
                save_transcript(
                    target_dir=target_dir,
                    order_num=idx,
                    total_count=total_videos,
                    video_info=video,
                    segments=segments,
                    format_type=self.format_type,
                )
                success_count += 1
            else:
                print(f"[!] Transcript unavailable for #{order_prefix} ({curr_id}).")
                failed_count += 1

        return {
            "total": total_videos,
            "success": success_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "destination": target_dir,
        }
