"""
Playwright Stealth Browser DOM Scraper for YouTube Modern UI
"""

import os
import time
from typing import List, Dict, Any, Optional
from .parsers import sanitize_filename
from .formatters import is_video_already_downloaded, save_transcript
from .constants import DEFAULT_USER_AGENT

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class BrowserScraper:
    """
    Automates transcript scraping via Playwright stealth browser DOM interaction.
    Bypasses IP blocks and BotGuard protections.
    """

    def __init__(
        self,
        output_dir: str = "transcripts",
        format_type: str = "txt",
        headless: bool = True,
    ):
        self.output_dir = output_dir
        self.format_type = format_type
        self.headless = headless

    def _create_context(self, playwright_instance):
        """Create a stealth anti-detection browser context."""
        chrome_bin = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
        browser = playwright_instance.chromium.launch(
            executable_path=chrome_bin,
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--window-size=1920,1080",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=DEFAULT_USER_AGENT,
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        return browser, context

    def fetch_video_transcript(self, page, video_url: str) -> Optional[List[Dict[str, Any]]]:
        """Scrapes transcript for a single video using active Playwright page."""
        try:
            page.goto(video_url, wait_until="commit", timeout=60000)
            time.sleep(6)

            # Scroll down to trigger metadata loading
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(3)

            # Expand description
            page.evaluate("""
                () => {
                    const more = document.querySelector('#description-inline-expander #expand, #expand, tp-yt-paper-button#expand');
                    if (more) more.click();
                }
            """)
            time.sleep(1.5)

            # Click Show transcript button
            clicked = page.evaluate("""
                () => {
                    const btn = document.querySelector('button[aria-label="Show transcript"]')
                             || Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Show transcript'));
                    if (btn) {
                        btn.click();
                        return true;
                    }
                    return false;
                }
            """)

            # Poll for segments
            for _ in range(6):
                time.sleep(1.5)
                segments = page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('transcript-segment-view-model, ytd-transcript-segment-renderer');
                        return Array.from(items).map(s => {
                            const ts = s.querySelector('.ytwTranscriptSegmentViewModelTimestamp, .segment-timestamp')?.innerText.trim() || '';
                            const txt = s.querySelector('span.ytAttributedStringHost, .segment-text')?.innerText.trim() || '';
                            return { timestamp: ts, text: txt };
                        }).filter(x => x.text);
                    }
                """)
                if segments:
                    return segments

            return None
        except Exception as e:
            print(f"[!] Browser scrape error on {video_url}: {e}")
            return None

    def scrape_single(self, video_url: str) -> Optional[List[Dict[str, Any]]]:
        """Standalone scrape for a single video using stealth browser."""
        if not HAS_PLAYWRIGHT:
            return None

        with sync_playwright() as p:
            browser, context = self._create_context(p)
            page = context.new_page()
            segments = self.fetch_video_transcript(page, video_url)
            browser.close()
            return segments

    def scrape_playlist(self, playlist_or_video_url: str):
        """Scrapes entire playlist using persistent browser session."""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright is not installed. Install via: pip install playwright")

        os.makedirs(self.output_dir, exist_ok=True)

        with sync_playwright() as p:
            browser, context = self._create_context(p)
            page = context.new_page()
            playlist_title = "Single_Videos"
            video_items = []

            if "list=" in playlist_or_video_url:
                print(f"[*] Navigating to playlist: {playlist_or_video_url}")
                page.goto(playlist_or_video_url, wait_until="commit")
                time.sleep(5)

                try:
                    title_el = page.locator("yt-dynamic-sizing-formatted-string#title, h1#title").first
                    if title_el.is_visible(timeout=3000):
                        playlist_title = title_el.inner_text().strip()
                except Exception:
                    playlist_title = "YouTube_Playlist"

                video_items = page.evaluate("""
                    () => {
                        const anchors = document.querySelectorAll('ytd-playlist-video-renderer a#video-title');
                        const results = [];
                        const seen = new Set();
                        anchors.forEach(a => {
                            const href = a.href;
                            const title = a.innerText.trim();
                            if (href && href.includes('/watch?v=') && !seen.has(href)) {
                                seen.add(href);
                                results.push({ url: href, title: title });
                            }
                        });
                        return results;
                    }
                """)
            else:
                video_items = [{"url": playlist_or_video_url, "title": "single_video"}]

            safe_playlist_name = sanitize_filename(playlist_title)
            target_subfolder = os.path.join(self.output_dir, safe_playlist_name)
            os.makedirs(target_subfolder, exist_ok=True)

            total_videos = len(video_items)
            pad_width = max(2, len(str(total_videos)))

            for idx, item in enumerate(video_items, start=1):
                url = item["url"]
                order_prefix = f"{idx:0{pad_width}d}"

                if is_video_already_downloaded(target_subfolder, order_prefix, "", self.format_type):
                    print(f"[⏩ Resumed] [{idx}/{total_videos}] #{order_prefix} already exists.")
                    continue

                print(f"\n--- [{idx}/{total_videos}] Browser fetching: {url} ---")
                segments = self.fetch_video_transcript(page, url)

                if segments:
                    title = page.title().replace(" - YouTube", "").strip() or item.get("title", f"video_{idx}")
                    video_info = {"id": f"vid_{idx}", "title": title, "url": url}
                    save_transcript(
                        target_dir=target_subfolder,
                        order_num=idx,
                        total_count=total_videos,
                        video_info=video_info,
                        segments=segments,
                        format_type=self.format_type,
                    )
                    print(f"[+] Successfully saved #{order_prefix} with {len(segments)} segments.")
                else:
                    print(f"[!] No DOM segments captured for #{order_prefix}.")

            browser.close()
