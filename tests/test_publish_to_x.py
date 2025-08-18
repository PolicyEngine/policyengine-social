#!/usr/bin/env python3
"""
Tests for X/Twitter publishing functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import yaml
from datetime import datetime, timedelta

from policyengine_social.publish import XPublisher


class TestXPublisher(unittest.TestCase):
    """Test cases for X/Twitter publishing."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'X_API_KEY': 'test_key',
            'X_API_SECRET': 'test_secret',
            'X_ACCESS_TOKEN': 'test_token',
            'X_ACCESS_SECRET': 'test_token_secret'
        })
        self.env_patcher.start()
        
        # Sample post data
        self.test_post = {
            'title': 'Test Post',
            'publish_at': datetime.now().isoformat(),
            'images': {
                'cover': {
                    'filename': 'test.png',
                    'url': 'https://example.com/test.png'
                }
            },
            'platforms': {
                'x': {
                    'thread': [
                        'First tweet in thread',
                        'Second tweet with details',
                        'Final tweet with link'
                    ],
                    'media': ['cover']
                }
            }
        }
    
    def tearDown(self):
        """Clean up."""
        self.env_patcher.stop()
    
    @patch('policyengine_social.publish.tweepy.Client')
    @patch('policyengine_social.publish.tweepy.API')
    def test_publisher_initialization(self, mock_api, mock_client):
        """Test XPublisher initialization with credentials."""
        publisher = XPublisher()
        
        # Should initialize both v2 client and v1.1 API
        mock_client.assert_called_once()
        mock_api.assert_called_once()
    
    @patch('policyengine_social.publish.tweepy.Client')
    @patch('policyengine_social.publish.tweepy.API')
    def test_publish_single_tweet(self, mock_api, mock_client):
        """Test publishing a single tweet without thread."""
        publisher = XPublisher()
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # Mock tweet response
        mock_response = MagicMock()
        mock_response.data = {'id': '123456789'}
        mock_client_instance.create_tweet.return_value = mock_response
        
        thread = ['Single tweet test']
        result = publisher.publish_thread(thread)
        
        # Should call create_tweet once
        mock_client_instance.create_tweet.assert_called_once_with(
            text='Single tweet test',
            media_ids=None
        )
        self.assertEqual(result, '123456789')
    
    @patch('policyengine_social.publish.tweepy.Client')
    @patch('policyengine_social.publish.tweepy.API')
    @patch('policyengine_social.publish.time.sleep')
    def test_publish_thread(self, mock_sleep, mock_api, mock_client):
        """Test publishing a multi-tweet thread."""
        publisher = XPublisher()
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # Mock tweet responses
        tweet_ids = ['111', '222', '333']
        responses = []
        for tweet_id in tweet_ids:
            mock_response = MagicMock()
            mock_response.data = {'id': tweet_id}
            responses.append(mock_response)
        
        mock_client_instance.create_tweet.side_effect = responses
        
        thread = ['Tweet 1', 'Tweet 2', 'Tweet 3']
        result = publisher.publish_thread(thread)
        
        # Should create 3 tweets
        self.assertEqual(mock_client_instance.create_tweet.call_count, 3)
        
        # First tweet should not be a reply
        first_call = mock_client_instance.create_tweet.call_args_list[0]
        self.assertNotIn('in_reply_to_tweet_id', first_call[1])
        
        # Subsequent tweets should be replies
        second_call = mock_client_instance.create_tweet.call_args_list[1]
        self.assertEqual(second_call[1]['in_reply_to_tweet_id'], '111')
        
        third_call = mock_client_instance.create_tweet.call_args_list[2]
        self.assertEqual(third_call[1]['in_reply_to_tweet_id'], '222')
        
        # Should return first tweet ID
        self.assertEqual(result, '111')
        
        # Should sleep between tweets
        self.assertEqual(mock_sleep.call_count, 2)
    
    @patch('policyengine_social.publish.tweepy.Client')
    @patch('policyengine_social.publish.tweepy.API')
    @patch('policyengine_social.publish.BlogImageExtractor')
    def test_media_upload(self, mock_extractor_class, mock_api, mock_client):
        """Test image upload for tweets."""
        publisher = XPublisher()
        mock_api_instance = MagicMock()
        mock_api.return_value = mock_api_instance
        
        # Mock image download and optimization
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.download_image.return_value = Path('test.png')
        mock_extractor.optimize_for_platform.return_value = Path('test_opt.png')
        
        # Mock media upload
        mock_media = MagicMock()
        mock_media.media_id_string = 'media_123'
        mock_api_instance.media_upload.return_value = mock_media
        
        images = {
            'cover': {'filename': 'test.png', 'url': 'https://example.com/test.png'}
        }
        
        result = publisher.upload_media(['cover'], images)
        
        # Should download, optimize, and upload
        mock_extractor.download_image.assert_called_once()
        mock_extractor.optimize_for_platform.assert_called_once()
        mock_api_instance.media_upload.assert_called_once()
        
        self.assertEqual(result, ['media_123'])
    
    @patch('policyengine_social.publish.tweepy.Client')
    @patch('policyengine_social.publish.tweepy.API')
    def test_publish_post_complete_flow(self, mock_api, mock_client):
        """Test complete post publishing flow."""
        publisher = XPublisher()
        
        # Mock successful publication
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.data = {'id': '999'}
        mock_client_instance.create_tweet.return_value = mock_response
        
        # Mock media upload
        with patch.object(publisher, 'upload_media', return_value=['media_123']):
            result = publisher.publish_post(self.test_post)
        
        self.assertTrue(result)
        
        # Check that published timestamp was added
        self.assertIn('published_at', self.test_post['platforms']['x'])
        self.assertIn('tweet_id', self.test_post['platforms']['x'])
    
    @patch('policyengine_social.publish.tweepy.Client')
    @patch('policyengine_social.publish.tweepy.API')
    def test_error_handling(self, mock_api, mock_client):
        """Test error handling during publication."""
        publisher = XPublisher()
        
        # Mock API error
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.create_tweet.side_effect = Exception("API Error")
        
        result = publisher.publish_post(self.test_post)
        
        # Should return False on error
        self.assertFalse(result)
        
        # Should not modify post data on failure
        self.assertNotIn('published_at', self.test_post['platforms']['x'])


class TestPublishingSchedule(unittest.TestCase):
    """Test scheduling and timing logic."""
    
    def test_should_publish_now(self):
        """Test logic for determining if post should be published."""
        # Post scheduled for past should publish
        past_post = {
            'publish_at': (datetime.now() - timedelta(hours=1)).isoformat()
        }
        
        # Post scheduled for future should not publish
        future_post = {
            'publish_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        past_time = datetime.fromisoformat(past_post['publish_at'])
        future_time = datetime.fromisoformat(future_post['publish_at'])
        
        self.assertLess(past_time, datetime.now())
        self.assertGreater(future_time, datetime.now())


if __name__ == '__main__':
    unittest.main()