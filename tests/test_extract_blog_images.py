#!/usr/bin/env python3
"""
Tests for blog image extraction functionality.
TDD approach - write tests first, then make them pass.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json

from policyengine_social.extract import BlogImageExtractor


class TestBlogImageExtractor(unittest.TestCase):
    """Test cases for BlogImageExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_slug = "test-blog-post"
        self.extractor = BlogImageExtractor(self.test_slug)

        # Mock blog post data
        self.mock_posts_json = [
            {
                "title": "Test Blog Post",
                "filename": "test-blog-post.md",
                "image": "test-cover.png",
                "date": "2024-01-01",
            }
        ]

        self.mock_markdown = """
# Test Blog Post

This is a test blog post with images.

![Alt text for image](../images/chart1.png)

Some more content here.

![](inline-image.jpg)

<img src="https://example.com/external.png" alt="External image">

And a final paragraph.
"""

    @patch("policyengine_social.extract.requests.get")
    def test_extract_cover_image(self, mock_get):
        """Test extraction of cover image from posts.json."""
        # Mock the API responses
        mock_get.return_value.json.return_value = self.mock_posts_json
        mock_get.return_value.text = self.mock_markdown

        images = self.extractor.extract_images()

        # Assert cover image is extracted correctly
        self.assertIn("cover", images)
        self.assertEqual(images["cover"]["filename"], "test-cover.png")
        self.assertEqual(images["cover"]["type"], "hero")
        self.assertTrue(images["cover"]["url"].endswith("test-cover.png"))

    @patch("policyengine_social.extract.requests.get")
    def test_extract_markdown_images(self, mock_get):
        """Test extraction of images from markdown content."""
        mock_get.return_value.json.return_value = self.mock_posts_json
        mock_get.return_value.text = self.mock_markdown

        images = self.extractor.extract_images()

        # Should find 2 markdown images
        self.assertIn("inline_1", images)
        self.assertIn("inline_2", images)

        # Check first markdown image
        self.assertEqual(images["inline_1"]["alt"], "Alt text for image")
        self.assertEqual(images["inline_1"]["filename"], "chart1.png")

        # Check second markdown image (no alt text)
        self.assertEqual(images["inline_2"]["filename"], "inline-image.jpg")

    @patch("policyengine_social.extract.requests.get")
    def test_extract_html_images(self, mock_get):
        """Test extraction of HTML img tags."""
        mock_get.return_value.json.return_value = self.mock_posts_json
        mock_get.return_value.text = self.mock_markdown

        images = self.extractor.extract_images()

        # Should find 1 HTML image
        self.assertIn("html_1", images)
        self.assertEqual(images["html_1"]["filename"], "external.png")
        self.assertEqual(images["html_1"]["url"], "https://example.com/external.png")

    @patch("policyengine_social.extract.requests.get")
    def test_no_images_in_post(self, mock_get):
        """Test handling of posts with no images."""
        mock_get.return_value.json.return_value = [
            {
                "title": "No Image Post",
                "filename": "test-blog-post.md",
                "date": "2024-01-01",
            }
        ]
        mock_get.return_value.text = "# Post with no images\n\nJust text content."

        images = self.extractor.extract_images()

        # Should return empty dict or minimal set
        self.assertEqual(len(images), 0)

    @patch("policyengine_social.extract.requests.get")
    @patch("policyengine_social.extract.Path.write_bytes")
    def test_download_image(self, mock_write, mock_get):
        """Test image download and caching."""
        # Mock successful download
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake image data"

        image_info = {"filename": "test.png", "url": "https://example.com/test.png"}

        result = self.extractor.download_image(image_info)

        # Should return path and write file
        self.assertIsNotNone(result)
        mock_write.assert_called_once_with(b"fake image data")

    @patch("policyengine_social.extract.Image.open")
    def test_optimize_for_platform_x(self, mock_image):
        """Test image optimization for X/Twitter."""
        # Mock PIL Image
        mock_img = MagicMock()
        mock_image.return_value = mock_img

        test_path = Path("test.png")
        result = self.extractor.optimize_for_platform(test_path, "x")

        # Should resize to X specifications
        mock_img.thumbnail.assert_called_once()
        call_args = mock_img.thumbnail.call_args[0]
        self.assertEqual(call_args[0], (1200, 675))  # X preferred dimensions

    @patch("policyengine_social.extract.Image.open")
    def test_optimize_for_platform_linkedin(self, mock_image):
        """Test image optimization for LinkedIn."""
        mock_img = MagicMock()
        mock_image.return_value = mock_img

        test_path = Path("test.png")
        result = self.extractor.optimize_for_platform(test_path, "linkedin")

        # Should resize to LinkedIn specifications
        mock_img.thumbnail.assert_called_once()
        call_args = mock_img.thumbnail.call_args[0]
        self.assertEqual(call_args[0], (1200, 627))  # LinkedIn dimensions

    def test_auto_select_images_x(self):
        """Test automatic image selection for X."""
        images = {
            "cover": {"type": "hero", "filename": "cover.png"},
            "inline_1": {"type": "supporting", "filename": "chart1.png"},
            "inline_2": {"type": "supporting", "filename": "chart2.png"},
            "inline_3": {"type": "supporting", "filename": "chart3.png"},
            "inline_4": {"type": "supporting", "filename": "chart4.png"},
        }

        selected = self.extractor.auto_select_images(images, "x")

        # Should select cover + up to 3 supporting images
        self.assertIn("cover", selected)
        self.assertLessEqual(len(selected), 4)  # X limit

    def test_auto_select_images_linkedin(self):
        """Test automatic image selection for LinkedIn."""
        images = {
            "cover": {"type": "hero", "filename": "cover.png"},
            "inline_1": {"type": "supporting", "filename": "chart1.png"},
        }

        selected = self.extractor.auto_select_images(images, "linkedin")

        # Should typically select just cover for LinkedIn
        self.assertIn("cover", selected)

    @patch("policyengine_social.extract.subprocess.run")
    def test_capture_screenshot(self, mock_run):
        """Test screenshot capture functionality."""
        mock_run.return_value.returncode = 0

        result = self.extractor.capture_screenshot(
            "https://policyengine.org/us", "homepage"
        )

        # Should call playwright with correct arguments
        self.assertIsNotNone(result)
        mock_run.assert_called_once()

        # Check playwright command structure
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "playwright")
        self.assertEqual(call_args[1], "screenshot")
        self.assertIn("https://policyengine.org/us", call_args)


class TestImageIntegration(unittest.TestCase):
    """Integration tests for image handling."""

    @patch("policyengine_social.extract.requests.get")
    def test_full_image_extraction_flow(self, mock_get):
        """Test complete flow from blog post to image manifest."""
        # Setup comprehensive mock data
        mock_posts = [
            {
                "title": "Policy Analysis Post",
                "filename": "policy-analysis.md",
                "image": "policy-cover.jpg",
            }
        ]

        mock_content = """
# Policy Analysis

![Impact chart](charts/impact.png)
![Distribution](charts/distribution.png)

<img src="/assets/calculator.png">
"""

        mock_get.return_value.json.return_value = mock_posts
        mock_get.return_value.text = mock_content

        extractor = BlogImageExtractor("policy-analysis")
        images = extractor.extract_images()

        # Should extract all image types
        self.assertEqual(len(images), 4)  # cover + 2 markdown + 1 html
        self.assertIn("cover", images)
        self.assertIn("inline_1", images)
        self.assertIn("inline_2", images)
        self.assertIn("html_1", images)

        # Test auto-selection for platforms
        x_selection = extractor.auto_select_images(images, "x")
        linkedin_selection = extractor.auto_select_images(images, "linkedin")

        # X should get multiple images
        self.assertGreater(len(x_selection), 1)
        # LinkedIn typically gets fewer
        self.assertLessEqual(len(linkedin_selection), len(x_selection))


if __name__ == "__main__":
    unittest.main()
