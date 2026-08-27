"""
Constants and DOM Selectors for YouTube Transcript Scraping
"""

DEFAULT_LANGUAGES = [
    "hi",
    "hi-orig",
    "en",
    "en-US",
    "en-GB",
    "en-IN",
    "mr",
    "ta",
    "te",
    "es",
    "fr",
    "de",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# DOM Selectors for YouTube Modern UI
SELECTORS = {
    "show_transcript_button": 'button[aria-label="Show transcript"]',
    "description_expander": "#description-inline-expander #expand, #expand, tp-yt-paper-button#expand",
    "transcript_panel": 'ytd-engagement-panel-section-list-renderer[target-id="PAmodern_transcript_view"]',
    "chapter_title": "h3.ytwTimelineChapterViewModelTitle, .ytwTimelineChapterViewModelTitle",
    "segment_item": "transcript-segment-view-model, ytd-transcript-segment-renderer",
    "timestamp": ".ytwTranscriptSegmentViewModelTimestamp, .segment-timestamp",
    "text": "span.ytAttributedStringHost, .segment-text",
}
