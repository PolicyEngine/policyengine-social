#!/usr/bin/env python3
"""
Publish posts to X (Twitter).
"""

import os
import yaml
import tweepy
from pathlib import Path
from datetime import datetime
import time
from typing import List, Dict

class XPublisher:
    def __init__(self):
        # Initialize X API client
        self.client = tweepy.Client(
            consumer_key=os.environ.get('X_API_KEY'),
            consumer_secret=os.environ.get('X_API_SECRET'),
            access_token=os.environ.get('X_ACCESS_TOKEN'),
            access_token_secret=os.environ.get('X_ACCESS_SECRET')
        )
        
        # For media upload (v1.1 API)
        auth = tweepy.OAuth1UserHandler(
            os.environ.get('X_API_KEY'),
            os.environ.get('X_API_SECRET'),
            os.environ.get('X_ACCESS_TOKEN'),
            os.environ.get('X_ACCESS_SECRET')
        )
        self.api = tweepy.API(auth)
    
    def publish_thread(self, thread: List[str], media_files: List[str] = None) -> str:
        """Publish a thread to X."""
        tweet_ids = []
        
        for i, tweet_text in enumerate(thread):
            # Add media only to first tweet
            media_ids = None
            if i == 0 and media_files:
                media_ids = self.upload_media(media_files)
            
            # Post tweet
            if i == 0:
                # First tweet in thread
                response = self.client.create_tweet(
                    text=tweet_text,
                    media_ids=media_ids
                )
            else:
                # Reply to previous tweet
                response = self.client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=tweet_ids[-1]
                )
            
            tweet_ids.append(response.data['id'])
            
            # Small delay between tweets to avoid rate limits
            if i < len(thread) - 1:
                time.sleep(2)
        
        return tweet_ids[0]  # Return first tweet ID
    
    def upload_media(self, media_refs: List[str], images_dict: Dict) -> List[str]:
        """Upload media files and return media IDs."""
        from policyengine_social.extract import BlogImageExtractor
        
        media_ids = []
        
        for img_ref in media_refs:
            if img_ref in images_dict:
                img_info = images_dict[img_ref]
                
                # Download/cache the image
                extractor = BlogImageExtractor("")  # Just for downloading
                img_path = extractor.download_image(img_info)
                
                if img_path:
                    # Optimize for X
                    optimized = extractor.optimize_for_platform(img_path, 'x')
                    
                    # Upload to X
                    media = self.api.media_upload(str(optimized))
                    media_ids.append(media.media_id_string)
                    print(f"✓ Uploaded to X: {img_info['filename']}")
        
        return media_ids if media_ids else None
    
    def publish_post(self, post_data: Dict) -> bool:
        """Publish a single post from YAML data."""
        try:
            x_content = post_data['platforms']['x']
            
            # Handle media files
            media_files = []
            if 'media' in x_content:
                media_files = [f"assets/{m}" for m in x_content['media']]
            
            # Publish thread
            tweet_id = self.publish_thread(x_content['thread'], media_files)
            
            print(f"✅ Published to X: https://twitter.com/PolicyEngine/status/{tweet_id}")
            
            # Update post status
            post_data['platforms']['x']['published_at'] = datetime.now().isoformat()
            post_data['platforms']['x']['tweet_id'] = tweet_id
            
            return True
            
        except Exception as e:
            print(f"❌ Error publishing to X: {e}")
            return False

def main():
    """Main function to publish all queued posts."""
    queue_dir = Path('posts/queue')
    publisher = XPublisher()
    
    for post_file in queue_dir.glob('*.yaml'):
        with open(post_file, 'r') as f:
            post_data = yaml.safe_load(f)
        
        # Check if it's time to publish
        publish_at = datetime.fromisoformat(post_data.get('publish_at', ''))
        if datetime.now() >= publish_at:
            print(f"Publishing: {post_file.name}")
            
            if publisher.publish_post(post_data):
                # Update and save the post data
                with open(post_file, 'w') as f:
                    yaml.dump(post_data, f, default_flow_style=False)
                
                # Move to published folder
                published_path = Path('posts/published') / post_file.name
                post_file.rename(published_path)
                print(f"Archived to: {published_path}")

if __name__ == '__main__':
    main()