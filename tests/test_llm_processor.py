import unittest
from yt_prompt.llm_processor import TranscriptLLMProcessor, MASTER_PROMPT_TEMPLATE


class TestLLMProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = TranscriptLLMProcessor(api_key="test_key")

    def test_parse_header_metadata(self):
        sample_text = (
            "Order: 5\n"
            "Title: Linear Regression Tutorial\n"
            "URL: https://www.youtube.com/watch?v=xyz123\n"
            "Video ID: xyz123\n\n"
            "[00:00] Hello everyone\n"
            "[00:15] Today we cover loss functions\n"
        )
        meta = self.processor.parse_header_metadata(sample_text)
        self.assertEqual(meta["order"], "5")
        self.assertEqual(meta["title"], "Linear Regression Tutorial")
        self.assertEqual(meta["url"], "https://www.youtube.com/watch?v=xyz123")
        self.assertEqual(meta["id"], "xyz123")

    def test_master_prompt_formatting(self):
        prompt = MASTER_PROMPT_TEMPLATE.format(
            title="Test Title",
            url="https://test.url",
            transcript_content="[00:00] Sample text",
        )
        self.assertIn("Final Complete English Transcript", prompt)
        self.assertIn("Intuitive Explanation", prompt)
        self.assertIn("Equations and Technical Concepts", prompt)
        self.assertIn("Fact Check and Important Nuance", prompt)
        self.assertIn("Visual Summary", prompt)
        self.assertIn("SOURCE VIDEO TITLE: Test Title", prompt)
        self.assertIn("[00:00] Sample text", prompt)


if __name__ == "__main__":
    unittest.main()
