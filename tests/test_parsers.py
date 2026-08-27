"""
Unit Tests for yt-prompt Parsers and Formatters
"""

import unittest
from yt_prompt.parsers import extract_video_id, extract_playlist_id, sanitize_filename
from yt_prompt.formatters import format_timestamp


class TestParsers(unittest.TestCase):

    def test_extract_video_id_standard(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_video_id_short(self):
        url = "https://youtu.be/dQw4w9WgXcQ?t=10"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_video_id_embed(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_playlist_id(self):
        url = "https://www.youtube.com/playlist?list=PLKnIA16_Rmvbr7zKYQuBfsVkjoLcJgxHH"
        self.assertEqual(extract_playlist_id(url), "PLKnIA16_Rmvbr7zKYQuBfsVkjoLcJgxHH")

    def test_sanitize_filename(self):
        dirty = "Tukaram Mundhe: The Singham? / Food Adulteration! [2026]"
        clean = sanitize_filename(dirty)
        self.assertNotIn(":", clean)
        self.assertNotIn("?", clean)
        self.assertNotIn("/", clean)
        self.assertNotIn("!", clean)

    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(0), "0:00")
        self.assertEqual(format_timestamp(65), "1:05")
        self.assertEqual(format_timestamp(3665), "1:01:05")


if __name__ == "__main__":
    unittest.main()
