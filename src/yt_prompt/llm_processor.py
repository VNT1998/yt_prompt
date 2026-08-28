"""
LLM Technical Transcript Processor & Educational Markdown Generator
Powered by Google Gemini API (with dotenv, retry handling, and mirror directory structure).
"""

import os
import time
import json
from typing import Optional, Dict, Any, List
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MASTER_PROMPT_TEMPLATE = """You are an expert Hinglish technical-transcript editor, machine-learning teacher, and fact-checker.

The transcript may contain Hindi, English, Hinglish, speech-recognition mistakes, broken grammar, incorrect technical terms, and incomplete equations.

## Non-Negotiable Completeness Rule

Create a **full, faithful English transcript—not a summary**.

- Preserve every substantive fact, claim, definition, qualification, example, comparison, equation, number, warning, conclusion, and teaching step from the source.
- Do not combine separate points merely to make the text shorter.
- Do not omit repeated statements if the repetition adds emphasis, clarification, or a new detail.
- You may remove only greetings, filler words, and repetitions that add no meaning.
- Correct obvious transcription and terminology errors silently, but never alter the speaker’s factual meaning.
- Do not invent missing explanations, code, numerical results, diagrams, or facts.
- If something cannot be recovered reliably, retain its position and write: “[This portion is unclear in the source transcript.]”
- Retain timestamps at every major topic change.
- Before answering, compare the final English draft against the source transcript internally and ensure every substantive point is represented.

# Final Complete English Transcript

Write the polished, complete English transcript here. Do not summarize it.

# Intuitive Explanation

Explain the material in simpler language without replacing or shortening the full transcript above. Clearly separate this explanation from the transcript.

# Equations and Technical Concepts

Present all recoverable formulas in Markdown LaTeX. Define symbols, weights, biases, activations, and outputs. Omit an equation only when it cannot be reliably reconstructed.

# Intuition and Derivations

If the video contains any kind of intuition, geometric visualization, mathematical derivation of the formula, or step-by-step logic, provide a dedicated, comprehensive breakdown describing it.

# Fact Check and Important Nuance

Fact-check the speaker’s claims without altering or omitting them from the final transcript.

| Timestamp | Claim | Verdict | Correct explanation or nuance | Source |
| --------- | ----- | ------- | ----------------------------- | ------ |

Use: **Accurate**, **Accurate but incomplete**, **Misleading / needs context**, **Inaccurate**, or **Unverifiable**.

# Key Takeaways

Provide a separate concise recap. This section must not replace any material in the complete transcript.

# Glossary

Define important terms in one sentence each.

# Comparison Table

If activation functions, algorithms, or techniques are discussed:

| Function / Algorithm | Formula | Output Range / Complexity | Strengths | Limitations | Typical Use |
| -------------------- | ------- | ------------------------- | --------- | ----------- | ----------- |

# Visual Summary

Create a Mermaid mind map and a simple flow diagram only from content present in the transcript.

# Questions and Answers

Create 8–12 study questions with answers based on the complete, fact-checked content.

**Question:** [Question]
**Answer:** [Verified, clear answer]
**Evidence:** [Timestamp and/or source]

-----------------------------------------------------------------
SOURCE VIDEO TITLE: {title}
SOURCE VIDEO URL: {url}

RAW SOURCE TRANSCRIPT:
{transcript_content}
"""


class TranscriptLLMProcessor:
    """
    Processes raw transcripts into structured educational markdown documents
    using Gemini API with exponential backoff and directory mirroring.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        max_retries: int = 5,
        base_delay: float = 5.0,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay

        if not self.api_key:
            # Check if set in .env in current or parent dirs
            pass

    def _get_api_url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def parse_header_metadata(self, content: str) -> Dict[str, str]:
        """Extract title, URL, order from transcript header if present."""
        meta = {"title": "Unknown Title", "url": "", "id": "", "order": ""}
        for line in content.split("\n")[:10]:
            if line.startswith("Title: "):
                meta["title"] = line.replace("Title: ", "").strip()
            elif line.startswith("URL: "):
                meta["url"] = line.replace("URL: ", "").strip()
            elif line.startswith("Video ID: "):
                meta["id"] = line.replace("Video ID: ", "").strip()
            elif line.startswith("Order: "):
                meta["order"] = line.replace("Order: ", "").strip()
        return meta

    def generate_markdown(self, transcript_text: str, title: str = "", url: str = "") -> str:
        """
        Sends transcript to Gemini with master prompt and returns generated markdown.
        Includes retry logic for rate limits (429) and server errors.
        """
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please export GEMINI_API_KEY='your-key' or add it to .env"
            )

        prompt = MASTER_PROMPT_TEMPLATE.format(
            title=title or "Machine Learning Tutorial",
            url=url or "N/A",
            transcript_content=transcript_text,
        )

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
            },
        }

        url = self._get_api_url()
        headers = {"Content-Type": "application/json"}

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    raise RuntimeError("Empty response from Gemini API.")
                elif resp.status_code in (429, 503, 500):
                    wait_time = self.base_delay * (2 ** (attempt - 1))
                    print(f"[!] Gemini API status {resp.status_code}. Retrying in {wait_time:.1f}s (attempt {attempt}/{self.max_retries})...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            except requests.exceptions.RequestException as e:
                wait_time = self.base_delay * (2 ** (attempt - 1))
                print(f"[!] Network error: {e}. Retrying in {wait_time:.1f}s (attempt {attempt}/{self.max_retries})...")
                time.sleep(wait_time)

        raise RuntimeError(f"Failed to generate LLM markdown after {self.max_retries} attempts.")

    def process_file(
        self,
        input_path: str,
        output_path: str,
        force: bool = False,
    ) -> bool:
        """
        Processes a single transcript file and saves the formatted markdown file.
        Returns True if processed, False if skipped.
        """
        if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            print(f"[⏩ Skipped] Already processed: {os.path.basename(output_path)}")
            return False

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip() or "NO_TRANSCRIPT_AVAILABLE" in content or "NOTICE: NO SUBTITLES" in content:
            print(f"[⚠️ Skipped] Empty/placeholder file: {os.path.basename(input_path)}")
            return False

        meta = self.parse_header_metadata(content)
        title = meta["title"]
        url = meta["url"]

        print(f"[*] Sending to LLM ({self.model}): '{title}' ({os.path.basename(input_path)})...")
        start_t = time.time()
        md_result = self.generate_markdown(content, title=title, url=url)
        duration = time.time() - start_t

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_result)

        print(f"[✓] Successfully generated and saved: {output_path} ({len(md_result)} chars in {duration:.1f}s)")
        return True

    def process_directory(
        self,
        input_dir: str = "transcripts",
        output_dir: str = "processed_transcripts",
        force: bool = False,
        delay_between: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Recursively processes all transcripts in input_dir, mirroring folder & file structure in output_dir.
        """
        if not os.path.exists(input_dir):
            print(f"[!] Input directory '{input_dir}' does not exist.")
            return {"total": 0, "processed": 0, "skipped": 0}

        # Discover all transcript files
        all_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in sorted(files):
                if file.endswith((".txt", ".md")) and not file.startswith("missing_files"):
                    full_in_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_in_path, input_dir)
                    # output name always ends in .md
                    base_name, _ = os.path.splitext(rel_path)
                    full_out_path = os.path.join(output_dir, f"{base_name}.md")
                    all_files.append((full_in_path, full_out_path, rel_path))

        total = len(all_files)
        print(f"[*] Found {total} transcripts across '{input_dir}' to process.")
        print(f"[*] Target Directory: '{os.path.abspath(output_dir)}'")
        print(f"[*] Model: {self.model}\n")

        processed_count = 0
        skipped_count = 0

        for idx, (in_p, out_p, rel_p) in enumerate(all_files, start=1):
            print(f"\n--- [{idx}/{total}] Processing: {rel_p} ---")
            try:
                success = self.process_file(in_p, out_p, force=force)
                if success:
                    processed_count += 1
                    if delay_between > 0 and idx < total:
                        time.sleep(delay_between)
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"[❌ Error] Failed to process {rel_p}: {e}")

        print("\n" + "=" * 65)
        print(f"[✓] LLM PROCESSING SUMMARY:")
        print(f"    - Total Files:      {total}")
        print(f"    - Processed (.md):  {processed_count}")
        print(f"    - Skipped/Existing: {skipped_count}")
        print(f"    - Output Folder:    {output_dir}")
        print("=" * 65)

        return {
            "total": total,
            "processed": processed_count,
            "skipped": skipped_count,
            "output_dir": output_dir,
        }
