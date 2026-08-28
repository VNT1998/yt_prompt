"""
AI Audio Speech-to-Text Transcriber for Missing YouTube Transcripts
Supports: Local Faster-Whisper (Offline CPU/GPU) & Cloud Gemini API
"""

import os
import subprocess
import tempfile
import time
from typing import List, Dict, Any, Optional
from .formatters import format_timestamp, save_transcript
from .parsers import sanitize_filename

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False


def scan_placeholders(target_dir: str) -> List[Dict[str, Any]]:
    """
    Scans target directory and returns metadata for all placeholder files.
    """
    if not os.path.exists(target_dir):
        return []

    placeholders = []
    files = sorted(os.listdir(target_dir))

    for f in files:
        if not f.endswith(".txt"):
            continue

        full_path = os.path.join(target_dir, f)
        try:
            with open(full_path, "r", encoding="utf-8") as fp:
                content = fp.read()
                if "NO_TRANSCRIPT_AVAILABLE" in content or "NOTICE: NO SUBTITLES" in content:
                    order = 0
                    title = ""
                    url = ""
                    v_id = ""

                    for line in content.split("\n"):
                        if line.startswith("Order: "):
                            order = int(line.replace("Order: ", "").strip())
                        elif line.startswith("Title: "):
                            title = line.replace("Title: ", "").strip()
                        elif line.startswith("URL: "):
                            url = line.replace("URL: ", "").strip()
                        elif line.startswith("Video ID: "):
                            v_id = line.replace("Video ID: ", "").strip()

                    placeholders.append({
                        "filename": f,
                        "order": order,
                        "title": title,
                        "url": url,
                        "id": v_id,
                        "filepath": full_path,
                    })
        except Exception:
            continue

    return placeholders


def download_audio_stream(video_url: str, output_template: str) -> Optional[str]:
    """
    Downloads low-bitrate audio stream using yt-dlp.
    """
    cmd = [
        "yt-dlp",
        "-f", "bestaudio/ba",
        "-x",
        "--audio-format", "m4a",
        "--audio-quality", "5",
        "-o", output_template,
        video_url,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Find the created file
        base_dir = os.path.dirname(output_template)
        base_name = os.path.basename(output_template).replace(".%(ext)s", "")
        for created in os.listdir(base_dir):
            if created.startswith(base_name):
                return os.path.join(base_dir, created)
        return None
    except Exception as e:
        print(f"[!] Error downloading audio for {video_url}: {e}")
        return None


class AudioTranscriber:
    """
    Transcribes audio for missing YouTube videos using local Whisper or Gemini.
    """

    def __init__(self, model_size: str = "base", compute_type: str = "int8"):
        self.model_size = model_size
        self.compute_type = compute_type
        self._model = None

    def _get_whisper_model(self):
        if not HAS_FASTER_WHISPER:
            raise RuntimeError(
                "faster-whisper is not installed. Install via: pip install faster-whisper"
            )
        if self._model is None:
            print(f"[*] Loading Faster-Whisper ({self.model_size}, {self.compute_type})...")
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type=self.compute_type
            )
        return self._model

    def transcribe_file(self, audio_path: str) -> List[Dict[str, Any]]:
        """Transcribe an audio file into timestamped segments."""
        model = self._get_whisper_model()
        segments, _ = model.transcribe(audio_path, beam_size=3)

        formatted_segments = []
        for s in segments:
            formatted_segments.append({
                "start": s.start,
                "duration": s.end - s.start,
                "timestamp": format_timestamp(s.start),
                "text": s.text.strip(),
            })

        return formatted_segments

    def process_placeholders(
        self,
        target_dir: str,
        total_videos: int = 134,
        format_type: str = "txt",
    ) -> Dict[str, Any]:
        """
        Scans directory, transcribes all placeholder files, and replaces them.
        """
        placeholders = scan_placeholders(target_dir)
        print(f"[*] Found {len(placeholders)} placeholder files to transcribe.")

        if not placeholders:
            print("[✓] No placeholders found. All files are complete!")
            return {"transcribed": 0, "total": 0}

        success_count = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            for idx, item in enumerate(placeholders, start=1):
                order_num = item["order"]
                v_title = item["title"]
                v_id = item["id"]
                v_url = item["url"]
                old_file = item["filepath"]

                print(f"\n--- [{idx}/{len(placeholders)}] AI Transcribing: #{order_num:03d} {v_title} ({v_id}) ---")

                # Step 1: Download audio
                audio_template = os.path.join(temp_dir, f"audio_{v_id}.%(ext)s")
                print(f"[*] Downloading audio stream from YouTube...")
                audio_path = download_audio_stream(v_url, audio_template)

                if not audio_path or not os.path.exists(audio_path):
                    print(f"[!] Failed to download audio for #{order_num:03d}.")
                    continue

                # Step 2: Transcribe audio
                print(f"[*] Running speech-to-text transcription...")
                try:
                    segments = self.transcribe_file(audio_path)
                    print(f"[✓] Successfully transcribed {len(segments)} segments!")

                    # Remove old placeholder file
                    if os.path.exists(old_file):
                        os.remove(old_file)

                    # Save real transcript
                    video_info = {"id": v_id, "title": v_title, "url": v_url}
                    save_transcript(
                        target_dir=target_dir,
                        order_num=order_num,
                        total_count=total_videos,
                        video_info=video_info,
                        segments=segments,
                        format_type=format_type,
                    )
                    success_count += 1
                except Exception as e:
                    print(f"[!] Transcription failed for #{order_num:03d}: {e}")
                finally:
                    # Clean temp audio
                    if audio_path and os.path.exists(audio_path):
                        try:
                            os.remove(audio_path)
                        except Exception:
                            pass

        return {"transcribed": success_count, "total": len(placeholders)}
