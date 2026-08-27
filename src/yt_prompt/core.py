"""
Core YouTube Transcript Scraper with Auto-Resume, Multi-Pass Retry, and Anti-Ban Engine
"""

import os
import time
import random
from typing import List, Dict, Any, Optional, Tuple
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
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )
    from youtube_transcript_api.proxies import GenericProxyConfig
    HAS_YTT = True
except ImportError:
    HAS_YTT = False
    YouTubeTranscriptApi = None


class PlaylistScraper:
    """
    Production-grade YouTube Playlist Transcript Scraper with auto-resume,
    anti-rate-limit cooldowns, and multi-pass recovery.
    """

    def __init__(
        self,
        output_dir: str = "transcripts",
        format_type: str = "txt",
        delay_seconds: float = 2.5,
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

    def fetch_single_transcript(self, video_id: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetch transcript via youtube-transcript-api.
        Returns: (segments, status_reason)
        """
        if not HAS_YTT:
            raise RuntimeError("youtube-transcript-api is not installed.")

        proxy_config = (
            GenericProxyConfig(http_url=self.proxy_url, https_url=self.proxy_url)
            if self.proxy_url
            else None
        )
        ytt = YouTubeTranscriptApi(proxy_config=proxy_config)

        # 1. Try direct fetch with specified languages
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
                    "duration": item.get("duration") if isinstance(item, dict) else item.duration,
                    "timestamp": format_timestamp(item.get("start") if isinstance(item, dict) else item.start),
                    "text": (item.get("text") if isinstance(item, dict) else item.text).replace("\n", " ").strip(),
                }
                for item in raw_items
            ], None
        except (TranscriptsDisabled, NoTranscriptFound):
            return None, "DISABLED"
        except VideoUnavailable:
            return None, "UNAVAILABLE"
        except Exception as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["429", "blocking requests", "ip", "too many requests", "requestblocked"]):
                raise e

            # 2. Fallback: List all available transcripts
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
                            "start": item.get("start") if isinstance(item, dict) else item.start,
                            "duration": item.get("duration") if isinstance(item, dict) else item.duration,
                            "timestamp": format_timestamp(item.get("start") if isinstance(item, dict) else item.start),
                            "text": (item.get("text") if isinstance(item, dict) else item.text).replace("\n", " ").strip(),
                        }
                        for item in fetched
                    ], None
                return None, "NOT_FOUND"
            except (TranscriptsDisabled, NoTranscriptFound):
                return None, "DISABLED"
            except Exception as inner_e:
                inner_msg = str(inner_e).lower()
                if any(k in inner_msg for k in ["429", "blocking requests", "ip", "requestblocked"]):
                    raise inner_e
                return None, str(inner_e)

    def fetch_with_backoff(self, video_id: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """Fetch transcript with exponential backoff on HTTP 429."""
        backoff_delays = [20.0, 45.0, 90.0, 180.0]

        for attempt in range(1, self.max_retries + 1):
            try:
                segments, reason = self.fetch_single_transcript(video_id)
                if reason in ("DISABLED", "UNAVAILABLE"):
                    return None, reason
                return segments, reason
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limited = any(
                    k in err_str
                    for k in ["429", "blocking requests", "too many requests", "ipblocked", "requestblocked"]
                )
                if is_rate_limited:
                    wait_seconds = (
                        backoff_delays[attempt - 1]
                        if attempt <= len(backoff_delays)
                        else 180.0
                    ) + random.uniform(1.0, 5.0)
                    print(
                        f"[!] YouTube Rate Limit (429) hit on video {video_id}!\n"
                        f"[⏳] Cooling down for {wait_seconds:.1f}s before retry (Attempt {attempt}/{self.max_retries})..."
                    )
                    time.sleep(wait_seconds)
                else:
                    return None, str(e)

        return None, "RATE_LIMIT_EXHAUSTED"

    def scrape(self, url: str, start_from: int = 1, auto_pass2: bool = True) -> Dict[str, Any]:
        """
        Scrapes all transcripts for a given playlist or single video.
        Includes automatic pass-2 recovery for any videos that faced temporary rate limits.
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
        disabled_count = 0
        rate_limited_videos = []

        print(f"[*] Destination Directory: {os.path.abspath(target_dir)}")
        print(f"[*] Resume Mode: {'ENABLED' if not self.force_overwrite else 'DISABLED'}")
        print(f"[*] Delay between videos: {self.delay_seconds:.1f}s\n")

        for idx, video in enumerate(videos, start=1):
            if idx < start_from:
                skipped_count += 1
                continue

            order_prefix = f"{idx:0{pad_width}d}"
            v_title = video.get("title", f"video_{idx}")
            curr_id = video.get("id", "")

            # 1. Resume check
            if not self.force_overwrite and is_video_already_downloaded(
                target_dir, order_prefix, curr_id, self.format_type
            ):
                print(f"[⏩ Resumed] [{idx}/{total_videos}] #{order_prefix} '{v_title}' already exists.")
                skipped_count += 1
                continue

            print(f"\n--- [{idx}/{total_videos}] Fetching: #{order_prefix} {v_title} ({curr_id}) ---")

            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds + random.uniform(0.5, 1.5))

            segments, reason = self.fetch_with_backoff(curr_id)

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
            elif reason == "DISABLED":
                print(f"[i] Subtitles explicitly disabled by creator on YouTube for #{order_prefix} ({curr_id}).")
                disabled_count += 1
            elif reason == "RATE_LIMIT_EXHAUSTED":
                print(f"[!] Cooldown exhausted on #{order_prefix} ({curr_id}). Queued for Pass 2.")
                rate_limited_videos.append((idx, video))
                # Cooldown barrier: pause 45s so next video doesn't immediately fail
                print("[⏳] Pausing 45s to let YouTube IP cooldown clear...")
                time.sleep(45)
            else:
                print(f"[!] Transcript unavailable for #{order_prefix} ({curr_id}) [Reason: {reason}].")

        # Pass 2 Recovery (if any videos were rate-limited)
        if auto_pass2 and rate_limited_videos:
            print("\n" + "=" * 65)
            print(f"[*] STARTING PASS 2 FOR {len(rate_limited_videos)} RATE-LIMITED VIDEOS...")
            print("=" * 65)
            time.sleep(15)

            for idx, video in rate_limited_videos:
                order_prefix = f"{idx:0{pad_width}d}"
                v_title = video.get("title", f"video_{idx}")
                curr_id = video.get("id", "")

                if is_video_already_downloaded(target_dir, order_prefix, curr_id, self.format_type):
                    continue

                print(f"\n--- [PASS 2] [{idx}/{total_videos}] #{order_prefix} {v_title} ({curr_id}) ---")
                time.sleep(self.delay_seconds + 2.0)
                segments, reason = self.fetch_with_backoff(curr_id)
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
                    print(f"[!] Pass 2 also failed for #{order_prefix} ({curr_id}) [Reason: {reason}].")

        final_files_count = len([f for f in os.listdir(target_dir) if f.endswith(f".{self.format_type}")]) if os.path.exists(target_dir) else 0

        return {
            "total": total_videos,
            "success": success_count,
            "skipped": skipped_count,
            "disabled": disabled_count,
            "final_files": final_files_count,
            "destination": target_dir,
        }
