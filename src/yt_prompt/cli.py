"""
Command Line Interface for yt-prompt
"""

import sys
import os
import argparse
from .core import PlaylistScraper
from .browser import BrowserScraper
from .transcribe import AudioTranscriber, scan_placeholders
from .llm_processor import TranscriptLLMProcessor
from .parsers import sanitize_filename, fetch_playlist_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-prompt",
        description="Scrape YouTube Playlist Transcripts with auto-resume, rate limiting, missing files tracking, and LLM processing.",
    )
    parser.add_argument("url", nargs="?", default=None, help="YouTube Playlist or Video URL")
    parser.add_argument(
        "-o",
        "--output",
        default="transcripts",
        help="Base directory for saving raw transcripts (default: 'transcripts')",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["txt", "md", "json", "all"],
        default="txt",
        help="Output format for raw transcripts: txt, md, json, all (default: 'txt')",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=45.0,
        help="Delay in seconds between video requests for anti-ban rate limiting (default: 45.0)",
    )
    parser.add_argument(
        "-s",
        "--start-from",
        type=int,
        default=1,
        help="Video index number to start/resume from (default: 1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download / re-process even if matching files already exist",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="HTTP/HTTPS/SOCKS proxy URL (e.g. 'http://user:pass@ip:port')",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use Playwright headless browser for DOM interaction instead of API",
    )
    parser.add_argument(
        "-t",
        "--transcribe-missing",
        action="store_true",
        help="Use AI speech-to-text to transcribe any missing videos in the playlist",
    )
    parser.add_argument(
        "--whisper-model",
        default="base",
        choices=["tiny", "base", "small", "medium"],
        help="Whisper model size for AI audio transcription (default: 'base')",
    )
    parser.add_argument(
        "-p",
        "--process",
        action="store_true",
        help="Process transcripts through LLM (Gemini) into structured educational Markdown documents",
    )
    parser.add_argument(
        "--processed-dir",
        default="processed_transcripts",
        help="Target directory for processed educational Markdown documents (default: 'processed_transcripts')",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.6-flash",
        help="Gemini model name for LLM processing (default: 'gemini-3.6-flash')",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API Key (default: reads GEMINI_API_KEY from environment or .env)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.url and not args.transcribe_missing and not args.process:
        parser.print_help()
        sys.exit(1)

    if args.url:
        if args.browser:
            scraper = BrowserScraper(
                output_dir=args.output,
                format_type=args.format,
                headless=True,
            )
            scraper.scrape_playlist(args.url)
        else:
            scraper = PlaylistScraper(
                output_dir=args.output,
                format_type=args.format,
                delay_seconds=args.delay,
                force_overwrite=args.force,
                proxy_url=args.proxy,
            )
            res = scraper.scrape(args.url, start_from=args.start_from)
            print("\n" + "=" * 65)
            print(f"[✓] SCRAPER SUMMARY:")
            print(f"    - Total Videos:          {res.get('total', 0)}")
            print(f"    - Full Transcripts:      {res.get('success', 0)}")
            print(f"    - Resumed / Existing:    {res.get('skipped', 0)}")
            print(f"    - Missing Transcripts:   {res.get('missing', 0)}")
            print(f"    - Total Files in Dir:    {res.get('final_files', 0)}")
            if "destination" in res:
                print(f"    - Folder Path:           {res['destination']}")
                print(f"    - Missing Tracker:       {os.path.join(res['destination'], 'missing_files.md')}")
            print("=" * 65)

            if args.transcribe_missing and res.get("missing", 0) > 0:
                target_folder = res.get("destination", args.output)
                transcriber = AudioTranscriber(model_size=args.whisper_model, api_key=args.api_key)
                transcriber.process_placeholders(
                    target_dir=target_folder,
                    total_videos=res.get("total", 134),
                    format_type=args.format,
                )

            if args.process:
                target_folder = res.get("destination", args.output)
                processor = TranscriptLLMProcessor(
                    api_key=args.api_key,
                    model=args.model,
                )
                processor.process_directory(
                    input_dir=target_folder,
                    output_dir=os.path.join(args.processed_dir, os.path.basename(target_folder)),
                    force=args.force,
                )

    elif args.transcribe_missing:
        target_dir = args.output
        if os.path.exists(target_dir):
            subdirs = [
                os.path.join(target_dir, d)
                for d in os.listdir(target_dir)
                if os.path.isdir(os.path.join(target_dir, d))
            ]
            folders_to_check = subdirs if subdirs else [target_dir]
            for folder in folders_to_check:
                missing_items = scan_placeholders(folder)
                if missing_items:
                    print(f"\n[*] Transcribing {len(missing_items)} missing videos in '{folder}'...")
                    transcriber = AudioTranscriber(model_size=args.whisper_model, api_key=args.api_key)
                    transcriber.process_placeholders(
                        target_dir=folder,
                        total_videos=len(os.listdir(folder)),
                        format_type=args.format,
                    )
        else:
            print(f"[!] Target directory '{target_dir}' does not exist.")

    elif args.process:
        # Standalone LLM processing on transcripts folder
        processor = TranscriptLLMProcessor(
            api_key=args.api_key,
            model=args.model,
        )
        processor.process_directory(
            input_dir=args.output,
            output_dir=args.processed_dir,
            force=args.force,
        )


if __name__ == "__main__":
    main()
