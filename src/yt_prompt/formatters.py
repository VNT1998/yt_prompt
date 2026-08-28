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
                if os.path.isfile(full_path) and os.path.getsize(full_path) > 30:
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
            "status": "AVAILABLE",
            "transcript": segments,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        saved_paths["json"] = json_path

    return saved_paths


def save_placeholder_transcript(
    target_dir: str,
    order_num: int,
    total_count: int,
    video_info: Dict[str, Any],
    reason: str = "NO_TRANSCRIPT_ON_YOUTUBE",
    format_type: str = "all",
) -> Dict[str, str]:
    """
    Save structured placeholder metadata for videos lacking YouTube subtitles,
    ensuring 100% continuous order numbering (001 to N).
    """
    os.makedirs(target_dir, exist_ok=True)
    pad_width = max(2, len(str(total_count)))
    order_prefix = f"{order_num:0{pad_width}d}"

    v_id = video_info.get("id", "unknown")
    v_title = video_info.get("title", f"video_{v_id}")
    safe_title = sanitize_filename(v_title)
    base_name = f"{order_prefix}_{safe_title}_{v_id}"

    saved_paths = {}

    # 1. Plain Text Placeholder
    if format_type in ("text", "txt", "all"):
        txt_path = os.path.join(target_dir, f"{base_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Order: {order_num}\n")
            f.write(f"Title: {v_title}\n")
            f.write(f"URL: {video_info.get('url')}\n")
            f.write(f"Video ID: {v_id}\n")
            f.write(f"Status: NO_TRANSCRIPT_AVAILABLE ({reason})\n\n")
            f.write("=" * 60 + "\n")
            f.write("NOTICE: NO SUBTITLES / TRANSCRIPT ON YOUTUBE\n")
            f.write("=" * 60 + "\n\n")
            f.write(
                "Subtitles or captions were not provided or auto-generated for this video "
                "by the creator on YouTube.\n"
            )
        saved_paths["txt"] = txt_path

    # 2. Markdown Placeholder
    if format_type in ("md", "markdown", "all"):
        md_path = os.path.join(target_dir, f"{base_name}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {order_prefix}. {v_title}\n\n")
            f.write(f"- **Order**: `{order_num}` of `{total_count}`\n")
            f.write(f"- **URL**: [{video_info.get('url')}]({video_info.get('url')})\n")
            f.write(f"- **Video ID**: `{v_id}`\n")
            f.write(f"- **Status**: ⚠️ `No transcript available on YouTube` (`{reason}`)\n\n")
            f.write("> [!NOTE]\n")
            f.write("> Closed captions or subtitles were not enabled for this video on YouTube.\n")
        saved_paths["md"] = md_path

    # 3. JSON Placeholder
    if format_type in ("json", "all"):
        json_path = os.path.join(target_dir, f"{base_name}.json")
        data = {
            "order": order_num,
            "id": v_id,
            "title": v_title,
            "url": video_info.get("url"),
            "segments_count": 0,
            "status": f"NO_TRANSCRIPT_AVAILABLE ({reason})",
            "transcript": [],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        saved_paths["json"] = json_path

    return saved_paths


def save_missing_files_tracker(
    target_dir: str,
    missing_items: List[Dict[str, Any]],
    total_videos: int,
    playlist_title: str = "Playlist",
) -> Dict[str, str]:
    """
    Maintains a dedicated tracker file (missing_files.md & missing_files.json)
    in the directory to track all videos lacking transcripts.
    """
    os.makedirs(target_dir, exist_ok=True)
    md_path = os.path.join(target_dir, "missing_files.md")
    json_path = os.path.join(target_dir, "missing_files.json")

    # 1. Write Markdown tracker
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 📋 Missing Transcripts Tracker: {playlist_title}\n\n")
        f.write(f"- **Total Videos in Playlist**: `{total_videos}`\n")
        f.write(f"- **Downloaded Transcripts**: `{total_videos - len(missing_items)}`\n")
        f.write(f"- **Missing Transcripts**: `{len(missing_items)}`\n\n")

        if missing_items:
            f.write("## ⚠️ Videos Lacking Subtitles on YouTube\n\n")
            f.write("| # | Order | Video ID | Video Title | Status / Reason | YouTube URL |\n")
            f.write("| :-: | :---: | :---: | :--- | :--- | :--- |\n")
            for idx, item in enumerate(missing_items, start=1):
                order_prefix = f"{item['order']:03d}"
                title = item.get("title", "Unknown").replace("|", "\\|")
                v_id = item.get("id", "")
                url = item.get("url", f"https://www.youtube.com/watch?v={v_id}")
                reason = item.get("reason", "NO_SUBTITLES_ON_YOUTUBE")
                f.write(f"| {idx} | **#{order_prefix}** | `{v_id}` | {title} | `{reason}` | [Watch]({url}) |\n")
            f.write("\n---\n")
            f.write("> [!TIP]\n")
            f.write("> You can automatically transcribe all missing videos using AI with:\n")
            f.write("> ```bash\n")
            f.write("> python3 main.py -t\n")
            f.write("> ```\n")
        else:
            f.write("✅ **All videos in this playlist have complete transcripts! Zero missing files.**\n")

    # 2. Write JSON tracker
    data = {
        "playlist": playlist_title,
        "total_videos": total_videos,
        "complete_count": total_videos - len(missing_items),
        "missing_count": len(missing_items),
        "missing_videos": missing_items,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"md": md_path, "json": json_path}

