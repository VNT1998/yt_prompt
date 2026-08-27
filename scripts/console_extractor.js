/**
 * YouTube Modern Transcript DOM Extractor (Browser DevTools Snippet)
 * ------------------------------------------------------------------
 * How to use:
 * 1. Open any YouTube video page in your browser.
 * 2. Open Developer Tools (F12 or Ctrl+Shift+I / Cmd+Option+I) -> Console tab.
 * 3. Paste this script and press Enter.
 * 4. It will expand the description, click "Show transcript", and extract all
 *    transcript segments line-by-line directly into your clipboard!
 */

(async function extractYouTubeTranscript() {
    console.log("%c[YouTube Transcript Scraper]%c Starting...", "color: #ff0000; font-weight: bold;", "color: inherit;");

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // 1. Expand description if needed
    let transcriptBtn = document.querySelector('button[aria-label="Show transcript"]')
        || Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Show transcript'));

    if (!transcriptBtn) {
        console.log("[*] Expanding description...");
        const expandBtn = document.querySelector('#description-inline-expander #expand, #expand, tp-yt-paper-button#expand');
        if (expandBtn) expandBtn.click();
        await sleep(1000);
        transcriptBtn = document.querySelector('button[aria-label="Show transcript"]')
            || Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Show transcript'));
    }

    // 2. Click "Show transcript" button
    const isPanelOpen = document.querySelector('ytd-engagement-panel-section-list-renderer[target-id="PAmodern_transcript_view"][visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED"]');
    if (!isPanelOpen && transcriptBtn) {
        console.log("[*] Clicking 'Show transcript' button...");
        transcriptBtn.click();
        await sleep(2000);
    }

    // 3. Locate the transcript engagement panel
    const panel = document.querySelector('ytd-engagement-panel-section-list-renderer[target-id="PAmodern_transcript_view"]')
        || document.querySelector('div#panels ytd-engagement-panel-section-list-renderer[visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED"]')
        || document.querySelector('ytd-transcript-renderer');

    if (!panel) {
        console.error("[!] Failed: Transcript engagement panel not found.");
        return;
    }

    const videoTitle = document.title.replace(" - YouTube", "").trim();
    const videoUrl = window.location.href;
    
    let plainTextLines = [
        `Title: ${videoTitle}`,
        `URL: ${videoUrl}\n`,
        "=".repeat(60),
        "TRANSCRIPT (LINE BY LINE)",
        "=".repeat(60) + "\n"
    ];

    const itemSections = panel.querySelectorAll('yt-item-section-renderer, ytd-item-section-renderer');
    let count = 0;

    if (itemSections.length > 0) {
        itemSections.forEach((section) => {
            const chapterEl = section.querySelector('.ytwTimelineChapterViewModelTitle, h3');
            const chapterTitle = chapterEl ? chapterEl.innerText.trim() : null;

            if (chapterTitle) {
                plainTextLines.push(`\n[${chapterTitle}]\n`);
            }

            const segments = section.querySelectorAll('transcript-segment-view-model, ytd-transcript-segment-renderer');
            segments.forEach((seg) => {
                const ts = seg.querySelector('.ytwTranscriptSegmentViewModelTimestamp, .segment-timestamp')?.innerText.trim() || "";
                const text = seg.querySelector('span.ytAttributedStringHost, .segment-text')?.innerText.trim().replace(/\s+/g, ' ') || "";

                if (text) {
                    plainTextLines.push(`[${ts}] ${text}`);
                    count++;
                }
            });
        });
    } else {
        const segments = panel.querySelectorAll('transcript-segment-view-model, ytd-transcript-segment-renderer');
        segments.forEach((seg) => {
            const ts = seg.querySelector('.ytwTranscriptSegmentViewModelTimestamp, .segment-timestamp')?.innerText.trim() || "";
            const text = seg.querySelector('span.ytAttributedStringHost, .segment-text')?.innerText.trim().replace(/\s+/g, ' ') || "";

            if (text) {
                plainTextLines.push(`[${ts}] ${text}`);
                count++;
            }
        });
    }

    if (count === 0) {
        console.warn("[!] No transcript segments found. Transcript might still be loading.");
        return;
    }

    const finalPlainText = plainTextLines.join("\n");

    try {
        await navigator.clipboard.writeText(finalPlainText);
        console.log(`%c[✓] SUCCESS! ${count} lines copied to clipboard (line-by-line separated)!`, "color: #00cc44; font-size: 14px; font-weight: bold;");
    } catch (e) {
        console.log("[✓] Extracted text:\n", finalPlainText);
    }

    return { totalLines: count, videoTitle, finalPlainText };
})();
