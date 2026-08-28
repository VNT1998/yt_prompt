"""
YouTube Transcript & Playlist Scraper
--------------------------------------
A high-resilience YouTube playlist transcript extractor with auto-resume,
anti-ban exponential backoff, and line-separated formatting.
"""

from .core import PlaylistScraper
from .browser import BrowserScraper
from .transcribe import AudioTranscriber, scan_placeholders
from .llm_processor import TranscriptLLMProcessor
from .parsers import extract_video_id, extract_playlist_id, fetch_video_title
from .formatters import format_timestamp, save_transcript, save_missing_files_tracker

__version__ = "1.0.0"
__all__ = [
    "PlaylistScraper",
    "BrowserScraper",
    "AudioTranscriber",
    "TranscriptLLMProcessor",
    "scan_placeholders",
    "extract_video_id",
    "extract_playlist_id",
    "fetch_video_title",
    "format_timestamp",
    "save_transcript",
    "save_missing_files_tracker",
]
