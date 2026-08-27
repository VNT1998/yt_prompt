#!/usr/bin/env python3
"""
YouTube Playlist Transcript Scraper (CLI Entry Point)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from yt_prompt.cli import main

if __name__ == "__main__":
    main()
