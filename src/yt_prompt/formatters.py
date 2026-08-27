"""
Transcript Output Formatters (Markdown, Text, JSON)
"""

import os
import json
from typing import List, Dict, Any
from .parsers import sanitize_filename


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS format."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def is_video_already_downloaded(
    target_dir: str, order_prefix: str, v_id: str, format_type: str
) -> bool:
    """Check if the target video file already exists and is non-empty."""
    if not os.path.exists(target_dir):
        return False

    ext_map = {
        "txt": [".txt"],
        "text": [".txt"],
        "md": [".md"],
        "markdown": [".md"],
        "json": [".json"],
        "all": [".txt", ".md", ".json"],
    }
    required_exts = ext_map.get(format_type, [".txt"])

    try:
        files = os.listdir(target_dir)
    except Exception:
        return False

    for ext in required_exts:
        matched = False
        for f in files:
            if f.startswith(f"{order_prefix}_") and f.endswith(ext):
                full_path = os.path.join(target_dir, f)
                if os.path.isfile(full_path) and os.path.getsize(full_path) > 50:
                    matched = True
                    break
        if not matched:
            return False
    return True


def save_transcript(
    target_dir: str,
    order_num: int,
    total_count: int,
    video_info: Dict[str, Any],
    segments: List[Dict[str, Any]],
    format_type: str = "all",
) -> Dict[str, str]:
    """
    Save transcript segments with ordered prefix and line-by-line separation.
    """
    os.makedirs(target_dir, exist_ok=True)
    pad_width = max(2, len(str(total_count)))
    order_prefix = f"{order_num:0{pad_width}d}"

    v_id = video_info.get("id", "unknown")
    v_title = video_info.get("title", f"video_{v_id}")
    safe_title = sanitize_filename(v_title)
    base_name = f"{order_prefix}_{safe_title}_{v_id}"

    saved_paths = {}

    # 1. Plain Text Format (Separated line by line)
    if format_type in ("text", "txt", "all"):
        txt_path = os.path.join(target_dir, f"{base_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Order: {order_num}\n")
            f.write(f"Title: {v_title}\n")
            f.write(f"URL: {video_info.get('url')}\n")
            f.write(f"Video ID: {v_id}\n\n")
            f.write("=" * 60 + "\n")
            f.write("TRANSCRIPT (LINE BY LINE)\n")
            f.write("=" * 60 + "\n\n")
            for seg in segments:
                ts = seg.get("timestamp", "0:00")
                text = seg.get("text", "").strip()
                if text:
                    f.write(f"[{ts}] {text}\n")
        saved_paths["txt"] = txt_path

    # 2. Markdown Format (Clean list items with timestamps)
    if format_type in ("md", "markdown", "all"):
        md_path = os.path.join(target_dir, f"{base_name}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {order_prefix}. {v_title}\n\n")
            f.write(f"- **Order**: `{order_num}` of `{total_count}`\n")
            f.write(f"- **URL**: [{video_info.get('url')}]({video_info.get('url')})\n")
            f.write(f"- **Video ID**: `{v_id}`\n\n")
            f.write("## Transcript\n\n")
            curr_chapter = None
            for seg in segments:
                if seg.get("chapter") and seg.get("chapter") != curr_chapter:
                    curr_chapter = seg["chapter"]
                    f.write(f"\n### {curr_chapter}\n\n")
                ts = seg.get("timestamp", "0:00")
                text = seg.get("text", "").strip()
                if text:
                    f.write(f"- **`[{ts}]`** {text}\n")
        saved_paths["md"] = md_path

    # 3. JSON Structured Format
    if format_type in ("json", "all"):
        json_path = os.path.join(target_dir, f"{base_name}.json")
        data = {
            "order": order_num,
            "id": v_id,
            "title": v_title,
            "url": video_info.get("url"),
            "segments_count": len(segments),
            "transcript": segments,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        saved_paths["json"] = json_path

    return saved_paths
