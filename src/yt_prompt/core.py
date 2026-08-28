"""
Core YouTube Transcript Scraper with Dual Engine (API + Stealth Browser Fallback)
and Automatic Sequence Placeholder Generation
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
    save_placeholder_transcript,
    save_missing_files_tracker,
)
from .browser import BrowserScraper

try:
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        IpBlocked,
        RequestBlocked,
    )
    from youtube_transcript_api.proxies import GenericProxyConfig
    HAS_YTT = True
except ImportError:
    HAS_YTT = False
    YouTubeTranscriptApi = None


class PlaylistScraper:
    """
    Production-grade YouTube Playlist Transcript Scraper.
    Dual Engine: Fast API -> Stealth Browser Fallback on IP Blocks.
    Ensures 100% continuous sequential files (001 to N) with metadata placeholders.
    """

    def __init__(
        self,
        output_dir: str = "transcripts",
        format_type: str = "txt",
        delay_seconds: float = 2.0,
        languages: List[str] = None,
        max_retries: int = 3,
        force_overwrite: bool = False,
        proxy_url: Optional[str] = None,
        save_placeholders: bool = True,
    ):
        self.output_dir = output_dir
        self.format_type = format_type
        self.delay_seconds = delay_seconds
        self.languages = languages or DEFAULT_LANGUAGES
        self.max_retries = max_retries
        self.force_overwrite = force_overwrite
        self.proxy_url = proxy_url
        self.save_placeholders = save_placeholders
        self.browser_scraper = BrowserScraper(
            output_dir=output_dir, format_type=format_type, headless=True
        )

    def fetch_single_transcript(
        self, video_id: str
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
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
            ], None
        except (TranscriptsDisabled, NoTranscriptFound):
            return None, "DISABLED"
        except VideoUnavailable:
            return None, "UNAVAILABLE"
        except Exception as e:
            err_msg = str(e).lower()
            if any(
                k in err_msg
                for k in [
                    "429",
                    "blocking requests",
                    "ip",
                    "too many requests",
                    "requestblocked",
                ]
            ):
                raise e

            # Fallback: List available
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
                    ], None
                return None, "NOT_FOUND"
            except (TranscriptsDisabled, NoTranscriptFound):
                return None, "DISABLED"
            except Exception as inner_e:
                inner_msg = str(inner_e).lower()
                if any(
                    k in inner_msg
                    for k in ["429", "blocking requests", "ip", "requestblocked"]
                ):
                    raise inner_e
                return None, str(inner_e)

    def fetch_video(
        self, video_id: str, video_url: str
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Dual Engine Fetcher:
        1. Fast API fetch
        2. On IP block / HTTP 429 -> Seamless Stealth Browser DOM Fallback
        """
        # Step 1: Fast API attempt
        try:
            segments, reason = self.fetch_single_transcript(video_id)
            if segments:
                return segments, None
            if reason in ("DISABLED", "UNAVAILABLE"):
                return None, reason
        except Exception as api_err:
            err_str = str(api_err).lower()
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
                print(f"[!] API rate limit / IP block detected for {video_id}.")
                print(f"[*] Switching to Stealth Browser DOM extraction for {video_url}...")
                browser_segments = self.browser_scraper.scrape_single(video_url)
                if browser_segments:
                    print(f"[✓] Stealth Browser successfully extracted {len(browser_segments)} segments!")
                    return browser_segments, None
                else:
                    return None, "NO_TRANSCRIPT_ON_YOUTUBE"
            return None, str(api_err)

        return None, "NO_TRANSCRIPT_ON_YOUTUBE"

    def scrape(
        self, url: str, start_from: int = 1, auto_pass2: bool = True
    ) -> Dict[str, Any]:
        """
        Scrapes all transcripts for a given playlist or single video.
        Ensures 100% unbroken sequential files (001 to N) with placeholders when captions are absent.
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
            return {"total": 0, "success": 0, "skipped": 0, "failed": 0, "placeholders": 0}

        safe_subfolder = sanitize_filename(playlist_title)
        target_dir = os.path.join(self.output_dir, safe_subfolder)
        os.makedirs(target_dir, exist_ok=True)

        total_videos = len(videos)
        pad_width = max(2, len(str(total_videos)))

        success_count = 0
        skipped_count = 0
        disabled_count = 0
        placeholder_count = 0

        print(f"[*] Destination Directory: {os.path.abspath(target_dir)}")
        print(
            f"[*] Resume Mode: {'ENABLED' if not self.force_overwrite else 'DISABLED'}"
        )
        print(f"[*] Delay between videos: {self.delay_seconds:.1f}s")
        print(f"[*] Sequential Placeholders: {'ENABLED' if self.save_placeholders else 'DISABLED'}\n")

        for idx, video in enumerate(videos, start=1):
            if idx < start_from:
                skipped_count += 1
                continue

            order_prefix = f"{idx:0{pad_width}d}"
            v_title = video.get("title", f"video_{idx}")
            curr_id = video.get("id", "")
            curr_url = video.get("url", f"https://www.youtube.com/watch?v={curr_id}")

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

            segments, reason = self.fetch_video(curr_id, curr_url)

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
                print(f"[✓] Saved #{order_prefix} ({len(segments)} segments)")
            else:
                if reason == "DISABLED":
                    print(f"[i] Subtitles explicitly disabled by creator for #{order_prefix} ({curr_id}).")
                    disabled_count += 1
                else:
                    print(f"[!] No subtitles available for #{order_prefix} ({curr_id}).")

                if self.save_placeholders:
                    save_placeholder_transcript(
                        target_dir=target_dir,
                        order_num=idx,
                        total_count=total_videos,
                        video_info=video,
                        reason=reason or "NO_SUBTITLES",
                        format_type=self.format_type,
                    )
                    placeholder_count += 1
                    print(f"[📝 Placeholder Saved] Created sequential file for #{order_prefix} with video metadata.")

        final_files_count = (
            len(
                [
                    f
                    for f in os.listdir(target_dir)
                    if f.endswith(f".{self.format_type}")
                ]
            )
            if os.path.exists(target_dir)
            else 0
        )

        failed_count = max(0, total_videos - success_count - skipped_count - placeholder_count)
        return {
            "total": total_videos,
            "success": success_count,
            "skipped": skipped_count,
            "placeholders": placeholder_count,
            "failed": failed_count,
            "disabled": disabled_count,
            "final_files": final_files_count,
            "destination": target_dir,
        }
