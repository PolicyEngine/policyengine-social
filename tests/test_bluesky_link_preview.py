"""Test Bluesky link preview functionality."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policyengine_social.publishers.bluesky import BlueSkyPublisher


class TestBlueSkyLinkPreview(unittest.TestCase):
    """Test Bluesky link preview generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the atproto client
        with patch('policyengine_social.publishers.bluesky.Client') as MockClient:
            self.mock_client = MagicMock()
            MockClient.return_value = self.mock_client
            
            # Create publisher instance
            self.publisher = BlueSkyPublisher(
                handle="test.bsky.social",
                password="test_password"
            )
            self.publisher.client = self.mock_client
    
    def test_extract_urls_from_text(self):
        """Test URL extraction from post text."""
        test_cases = [
            ("Check out https://policyengine.org", ["https://policyengine.org"]),
            ("Visit http://example.com and https://test.org", ["http://example.com", "https://test.org"]),
            ("No URLs here", []),
            ("Multiple: https://a.com https://b.com", ["https://a.com", "https://b.com"]),
        ]
        
        for text, expected_urls in test_cases:
            urls = self.publisher._extract_urls(text)
            self.assertEqual(urls, expected_urls)
    
    @patch('policyengine_social.publishers.bluesky.requests.get')
    def test_fetch_url_metadata(self, mock_get):
        """Test fetching Open Graph metadata from URL."""
        # Mock response with Open Graph tags
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <head>
            <meta property="og:title" content="Test Title">
            <meta property="og:description" content="Test Description">
            <meta property="og:image" content="https://example.com/image.jpg">
        </head>
        </html>
        """
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        metadata = self.publisher._fetch_url_metadata("https://example.com")
        
        self.assertEqual(metadata['title'], "Test Title")
        self.assertEqual(metadata['description'], "Test Description")
        self.assertEqual(metadata['image'], "https://example.com/image.jpg")
    
    @patch('policyengine_social.publishers.bluesky.requests.get')
    def test_fetch_url_metadata_fallback(self, mock_get):
        """Test fallback when Open Graph tags are missing."""
        # Mock response without Open Graph tags
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <head>
            <title>Fallback Title</title>
            <meta name="description" content="Fallback Description">
        </head>
        </html>
        """
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        metadata = self.publisher._fetch_url_metadata("https://example.com")
        
        self.assertEqual(metadata['title'], "Fallback Title")
        self.assertEqual(metadata['description'], "Fallback Description")
        self.assertIsNone(metadata['image'])
    
    @patch('policyengine_social.publishers.bluesky.requests.get')
    def test_post_with_link_preview(self, mock_get):
        """Test posting with automatic link preview generation."""
        # Mock URL metadata fetch
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <head>
            <meta property="og:title" content="PolicyEngine NSF Grant">
            <meta property="og:description" content="We received a $300,000 grant">
            <meta property="og:image" content="https://policyengine.org/image.png">
        </head>
        </html>
        """
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Mock image download for thumbnail
        mock_image_response = MagicMock()
        mock_image_response.content = b"fake_image_data"
        mock_image_response.status_code = 200
        
        def side_effect(url, **kwargs):
            if url.endswith('.png') or url.endswith('.jpg'):
                return mock_image_response
            return mock_response
        
        mock_get.side_effect = side_effect
        
        # Mock blob upload
        mock_blob_response = MagicMock()
        mock_blob_response.blob = MagicMock()
        mock_blob_response.blob.model_dump = MagicMock(return_value={
            "ref": {"link": "bafkreitest123"},
            "mimeType": "image/png",
            "size": 12345
        })
        self.mock_client.upload_blob.return_value = mock_blob_response
        
        # Mock send_post
        mock_post_response = MagicMock()
        mock_post_response.uri = "at://did:plc:test/app.bsky.feed.post/abc123"
        mock_post_response.cid = "bafytest456"
        self.mock_client.send_post.return_value = mock_post_response
        
        # Test posting with URL
        result = self.publisher.post(
            text="Check out our grant: https://policyengine.org/us/research/nsf-grant"
        )
        
        # Verify success
        self.assertTrue(result['success'])
        
        # Verify send_post was called with external embed
        self.mock_client.send_post.assert_called_once()
        call_args = self.mock_client.send_post.call_args
        
        # Check that external embed was created
        if 'embed' in call_args.kwargs:
            embed = call_args.kwargs['embed']
            self.assertEqual(embed['$type'], 'app.bsky.embed.external')
            self.assertIn('external', embed)
            self.assertEqual(embed['external']['uri'], 'https://policyengine.org/us/research/nsf-grant')
            self.assertEqual(embed['external']['title'], 'PolicyEngine NSF Grant')
            self.assertEqual(embed['external']['description'], 'We received a $300,000 grant')
    
    def test_post_with_image_takes_precedence(self):
        """Test that explicit images take precedence over link previews."""
        # Mock blob upload for image
        mock_blob_response = MagicMock()
        mock_blob_response.blob = MagicMock()
        mock_blob_response.blob.model_dump = MagicMock(return_value={
            "ref": {"link": "bafkreitest123"},
            "mimeType": "image/png",
            "size": 12345
        })
        self.mock_client.upload_blob.return_value = mock_blob_response
        
        # Mock send_post
        mock_post_response = MagicMock()
        mock_post_response.uri = "at://did:plc:test/app.bsky.feed.post/abc123"
        mock_post_response.cid = "bafytest456"
        self.mock_client.send_post.return_value = mock_post_response
        
        # Test posting with both image and URL
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"fake_image_data"
            
            result = self.publisher.post(
                text="Check out https://policyengine.org with image",
                images=["/path/to/image.png"]
            )
        
        # Verify success
        self.assertTrue(result['success'])
        
        # Verify image embed was used, not external embed
        call_args = self.mock_client.send_post.call_args
        if 'embed' in call_args.kwargs:
            embed = call_args.kwargs['embed']
            self.assertEqual(embed['$type'], 'app.bsky.embed.images')


if __name__ == '__main__':
    unittest.main()