"""
Command Line Interface for yt-prompt
"""

import sys
import argparse
from .core import PlaylistScraper
from .browser import BrowserScraper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-prompt",
        description="Scrape YouTube Playlist Transcripts with auto-resume, rate-limit protection, and line-separated output.",
    )
    parser.add_argument("url", help="YouTube Playlist or Video URL")
    parser.add_argument(
        "-o",
        "--output",
        default="transcripts",
        help="Base directory for saving transcripts (default: 'transcripts')",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["txt", "md", "json", "all"],
        default="txt",
        help="Output format: txt, md, json, all (default: 'txt')",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between video requests for anti-ban rate limiting (default: 2.0)",
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
        help="Force re-download even if matching files already exist",
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
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

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
        print(f"[✓] SUMMARY:")
        print(f"    - Total:      {res['total']}")
        print(f"    - Downloaded: {res['success']}")
        print(f"    - Resumed:    {res['skipped']}")
        print(f"    - Failed:     {res['failed']}")
        if "destination" in res:
            print(f"    - Path:       {res['destination']}")
        print("=" * 65)


if __name__ == "__main__":
    main()
