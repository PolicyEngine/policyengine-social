#!/usr/bin/env python3
"""
Tests for social post generation functionality.
"""
from datetime import datetime

import unittest
from unittest.mock import patch, MagicMock

from policyengine_social.generate import SocialPostGenerator


class TestSocialPostGenerator(unittest.TestCase):
    """Test cases for social post generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_slug = "test-policy-reform"
        self.test_title = "Test Policy Reform Analysis"
        self.generator = SocialPostGenerator(self.test_slug, self.test_title)

    def test_blog_url_generation(self):
        """Test that blog URLs are generated correctly."""
        self.assertEqual(
            self.generator.blog_url,
            f"https://policyengine.org/us/blog/{self.test_slug}",
        )

    def test_x_thread_generation(self):
        """Test X/Twitter thread generation."""
        thread = self.generator.generate_x_thread()

        # Should generate multi-tweet thread
        self.assertIsInstance(thread, list)
        self.assertGreater(len(thread), 1)

        # First tweet should be engaging
        self.assertIn(self.test_title, thread[0])

        # Last tweet should have CTA with link
        self.assertIn(self.generator.blog_url, thread[-1])
        self.assertIn("Read", thread[-1])

    def test_linkedin_post_generation(self):
        """Test LinkedIn post generation."""
        post = self.generator.generate_linkedin_post()

        # Should be single comprehensive post
        self.assertIsInstance(post, str)

        # Should include key elements
        self.assertIn(self.test_title, post)
        self.assertIn(self.generator.blog_url, post)
        self.assertIn("#", post)  # Hashtags

        # Should be professional length (not too short)
        self.assertGreater(len(post), 200)

    @patch("policyengine_social.generate.BlogImageExtractor")
    def test_post_yaml_generation(self, mock_extractor_class):
        """Test complete YAML structure generation."""
        # Mock image extraction
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_images.return_value = {
            "cover": {"filename": "test.png", "type": "hero"}
        }
        mock_extractor.auto_select_images.return_value = ["cover"]

        yaml_data = self.generator.generate_post_yaml()

        # Check structure
        self.assertIn("title", yaml_data)
        self.assertIn("source", yaml_data)
        self.assertIn("url", yaml_data)
        self.assertIn("publish_at", yaml_data)
        self.assertIn("platforms", yaml_data)
        self.assertIn("metadata", yaml_data)

        # Check platforms
        self.assertIn("x", yaml_data["platforms"])
        self.assertIn("linkedin", yaml_data["platforms"])

        # Check X structure
        x_data = yaml_data["platforms"]["x"]
        self.assertIn("thread", x_data)
        self.assertIn("media", x_data)
        self.assertIn("hashtags", x_data)

        # Check LinkedIn structure
        linkedin_data = yaml_data["platforms"]["linkedin"]
        self.assertIn("text", linkedin_data)
        self.assertIn("media", linkedin_data)

    def test_grant_post_specific_content(self):
        """Test grant-specific content generation."""
        grant_generator = SocialPostGenerator(
            "nsf-grant-announcement", "NSF Awards $300K Grant"
        )

        thread = grant_generator.generate_x_thread()

        # Should detect grant keyword and adjust tone
        self.assertIn("🎉", thread[0])
        self.assertIn("excited", thread[0].lower())

    def test_publish_time_scheduling(self):
        """Test that publish times are set correctly."""
        yaml_data = self.generator.generate_post_yaml()

        publish_at = datetime.fromisoformat(yaml_data["publish_at"])
        now = datetime.now()

        # Should be scheduled for future
        self.assertGreater(publish_at, now)

        # Should be at 10 AM
        self.assertEqual(publish_at.hour, 10)
        self.assertEqual(publish_at.minute, 0)

    def test_metadata_inclusion(self):
        """Test metadata is properly included."""
        yaml_data = self.generator.generate_post_yaml()

        metadata = yaml_data["metadata"]
        self.assertIn("generated_at", metadata)
        self.assertIn("generator_version", metadata)
        self.assertIn("auto_selected_images", metadata)

        # Generated timestamp should be recent
        generated = datetime.fromisoformat(metadata["generated_at"])
        time_diff = datetime.now() - generated
        self.assertLess(time_diff.total_seconds(), 60)  # Within last minute


class TestContentVariations(unittest.TestCase):
    """Test different types of blog post content."""

    def test_research_post(self):
        """Test generation for research/analysis posts."""
        generator = SocialPostGenerator(
            "poverty-impact-analysis", "New Research: Poverty Impact of Tax Reform"
        )

        thread = generator.generate_x_thread()
        linkedin = generator.generate_linkedin_post()

        # Should emphasize data and findings
        self.assertIn("New from PolicyEngine", thread[0])
        self.assertIn("analysis", linkedin.lower())

    def test_feature_announcement(self):
        """Test generation for feature announcements."""
        generator = SocialPostGenerator(
            "new-calculator-features", "Introducing State-Level Analysis"
        )

        thread = generator.generate_x_thread()

        # Should focus on capabilities
        self.assertIn("Introducing", thread[0])

    def test_policy_comparison(self):
        """Test generation for policy comparison posts."""
        generator = SocialPostGenerator(
            "policy-a-vs-policy-b", "Comparing Two Approaches to Child Tax Credit"
        )

        linkedin = generator.generate_linkedin_post()

        # Should highlight comparison aspect
        self.assertIn("Comparing", linkedin)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in post generation."""

    @patch("policyengine_social.generate.requests.get")
    def test_blog_fetch_failure(self, mock_get):
        """Test handling of blog fetch failures."""
        mock_get.side_effect = Exception("Network error")

        generator = SocialPostGenerator("test-slug")

        # Should have fallback content
        self.assertIsNotNone(generator.content)
        self.assertIn("title", generator.content)

    @patch("policyengine_social.generate.BlogImageExtractor")
    def test_image_extraction_failure(self, mock_extractor_class):
        """Test graceful handling of image extraction failures."""
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_images.side_effect = Exception("Image error")

        generator = SocialPostGenerator("test-slug")

        # Should still generate post without images
        yaml_data = generator.generate_post_yaml()
        self.assertIsNotNone(yaml_data)


if __name__ == "__main__":
    unittest.main()
