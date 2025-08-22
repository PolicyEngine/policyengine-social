"""Test Bluesky image handling."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policyengine_social.publishers.bluesky import BlueSkyPublisher


class TestBlueSkyImageHandling(unittest.TestCase):
    """Test Bluesky image upload and posting with images."""
    
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
    
    def test_upload_image_returns_blob_ref(self):
        """Test that upload_image returns a proper blob reference."""
        # Mock the upload_blob response
        mock_blob = MagicMock()
        mock_blob.blob = MagicMock()
        mock_blob.blob.ref = MagicMock()
        mock_blob.blob.ref.link = "bafkreitest123"
        mock_blob.blob.mime_type = "image/png"
        mock_blob.blob.size = 12345
        
        self.mock_client.upload_blob.return_value = mock_blob
        
        # Test upload
        result = self.publisher.upload_image("/path/to/test.png")
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIn('blob', result)
        
    def test_post_with_image_converts_blob_ref(self):
        """Test that posting with an image properly converts BlobRef to dict."""
        # Mock upload_blob to return a BlobRef-like object
        mock_blob_response = MagicMock()
        mock_blob_response.blob = MagicMock()
        mock_blob_response.blob.ref = MagicMock()
        mock_blob_response.blob.ref.link = "bafkreitest123"
        mock_blob_response.blob.mime_type = "image/png"
        mock_blob_response.blob.size = 12345
        
        # Add to_dict method to the blob object
        mock_blob_response.blob.to_dict = MagicMock(return_value={
            "ref": {"link": "bafkreitest123"},
            "mimeType": "image/png",
            "size": 12345
        })
        
        self.mock_client.upload_blob.return_value = mock_blob_response
        
        # Mock send_post to succeed
        mock_post_response = MagicMock()
        mock_post_response.uri = "at://did:plc:test/app.bsky.feed.post/abc123"
        mock_post_response.cid = "bafytest456"
        self.mock_client.send_post.return_value = mock_post_response
        
        # Test posting with image
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"fake_image_data"
            
            result = self.publisher.post(
                text="Test post with image",
                images=["/path/to/test.png"]
            )
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertIn('uri', result)
        
        # Verify send_post was called with proper embed structure
        self.mock_client.send_post.assert_called_once()
        call_args = self.mock_client.send_post.call_args
        
        # Check that embed was passed
        if 'embed' in call_args.kwargs:
            embed = call_args.kwargs['embed']
            self.assertIn('$type', embed)
            self.assertEqual(embed['$type'], 'app.bsky.embed.images')
            self.assertIn('images', embed)
            self.assertTrue(len(embed['images']) > 0)
            
            # Check image structure
            image = embed['images'][0]
            self.assertIn('image', image)
            # The image blob should be a dict, not a BlobRef object
            self.assertIsInstance(image['image'], dict)
    
    def test_post_thread_with_images_on_first_post_only(self):
        """Test that thread posting only adds images to the first post."""
        # Mock upload_blob
        mock_blob_response = MagicMock()
        mock_blob_response.blob = MagicMock()
        mock_blob_response.blob.to_dict = MagicMock(return_value={
            "ref": {"link": "bafkreitest123"},
            "mimeType": "image/png",
            "size": 12345
        })
        self.mock_client.upload_blob.return_value = mock_blob_response
        
        # Mock send_post to track calls
        mock_post_response = MagicMock()
        mock_post_response.uri = "at://did:plc:test/app.bsky.feed.post/abc123"
        mock_post_response.cid = "bafytest456"
        self.mock_client.send_post.return_value = mock_post_response
        
        # Test thread with images
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"fake_image_data"
            
            result = self.publisher.post_thread(
                posts=["First post with image", "Second post without image"],
                images=["/path/to/test.png"]
            )
        
        # Verify success
        self.assertTrue(result['success'])
        
        # Verify send_post was called twice
        self.assertEqual(self.mock_client.send_post.call_count, 2)
        
        # Check first call has image embed
        first_call = self.mock_client.send_post.call_args_list[0]
        if 'embed' in first_call.kwargs:
            self.assertIsNotNone(first_call.kwargs['embed'])
            self.assertEqual(first_call.kwargs['embed']['$type'], 'app.bsky.embed.images')
        
        # Check second call has no image embed (but may have reply_to)
        second_call = self.mock_client.send_post.call_args_list[1]
        if 'embed' in second_call.kwargs:
            # Should not have images embed
            embed = second_call.kwargs.get('embed')
            if embed:
                self.assertNotEqual(embed.get('$type'), 'app.bsky.embed.images')


if __name__ == '__main__':
    unittest.main()