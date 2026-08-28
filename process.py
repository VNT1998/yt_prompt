#!/usr/bin/env python3
"""
Direct LLM Processing Script
Processes all transcript files through Gemini LLM using Master Prompt into educational .md files.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from yt_prompt.llm_processor import TranscriptLLMProcessor


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Process transcripts through Gemini LLM into structured educational Markdown.")
    parser.add_argument("-i", "--input", default="transcripts", help="Input directory containing raw transcripts (default: 'transcripts')")
    parser.add_argument("-o", "--output", default="processed_transcripts", help="Output directory for processed markdown (default: 'processed_transcripts')")
    parser.add_argument("-m", "--model", default="gemini-2.5-flash", help="Gemini model name (default: 'gemini-2.5-flash')")
    parser.add_argument("--force", action="store_true", help="Force re-processing even if output file already exists")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between API calls in seconds (default: 2.0)")
    parser.add_argument("--api-key", default=None, help="Gemini API Key (optional, defaults to GEMINI_API_KEY env)")
    args = parser.parse_args()

    processor = TranscriptLLMProcessor(api_key=args.api_key, model=args.model)
    processor.process_directory(
        input_dir=args.input,
        output_dir=args.output,
        force=args.force,
        delay_between=args.delay,
    )


if __name__ == "__main__":
    main()
