#!/usr/bin/env python3
"""
Main entry point for yt-prompt
"""

import sys
import os

# Ensure src is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from yt_prompt.cli import main

if __name__ == "__main__":
    main()
