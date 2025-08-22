"""Bluesky publisher for PolicyEngine social media posts."""

import os
import logging
from typing import Dict, List, Optional
from atproto import Client, client_utils
import time

logger = logging.getLogger(__name__)


class BlueSkyPublisher:
    """Publisher for Bluesky social network."""
    
    def __init__(self, handle: str = None, password: str = None):
        """Initialize Bluesky publisher.
        
        Args:
            handle: Bluesky handle (e.g., "policyengine.bsky.social")
            password: App password for the account
        """
        self.handle = handle or os.getenv("BLUESKY_HANDLE")
        self.password = password or os.getenv("BLUESKY_PASSWORD")
        self.client = None
        
        if self.handle and self.password:
            self.login()
    
    def login(self):
        """Login to Bluesky."""
        try:
            self.client = Client()
            self.client.login(self.handle, self.password)
            logger.info(f"Successfully logged in to Bluesky as {self.handle}")
        except Exception as e:
            logger.error(f"Failed to login to Bluesky: {e}")
            raise
    
    def post(
        self,
        text: str,
        images: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict:
        """Post to Bluesky.
        
        Args:
            text: Post text (max 300 characters)
            images: Optional list of image paths
            reply_to: Optional post URI to reply to
            
        Returns:
            Response dict with post details
        """
        if not self.client:
            return {"success": False, "error": "Not logged in"}
        
        try:
            # Check text length
            if len(text) > 300:
                logger.warning(f"Text too long for Bluesky ({len(text)} chars), truncating")
                text = text[:297] + "..."
            
            # Build the post
            post_builder = client_utils.TextBuilder()
            post_builder.text(text)
            
            # Handle images if provided
            embed = None
            if images:
                image_alts = []
                uploaded_images = []
                
                for img_path in images[:4]:  # Bluesky supports up to 4 images
                    if os.path.exists(img_path):
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        
                        # Upload image
                        upload = self.client.upload_blob(img_data)
                        uploaded_images.append(upload.blob)
                        image_alts.append(os.path.basename(img_path))
                
                if uploaded_images:
                    embed = {
                        "$type": "app.bsky.embed.images",
                        "images": [
                            {"alt": alt, "image": img.to_dict()}
                            for alt, img in zip(image_alts, uploaded_images)
                        ]
                    }
            
            # Create the post
            post_data = {
                "text": post_builder.build_text(),
                "facets": post_builder.build_facets(),
            }
            
            if embed:
                post_data["embed"] = embed
            
            if reply_to:
                # Parse reply reference
                post_data["reply"] = {
                    "parent": {"uri": reply_to},
                    "root": {"uri": reply_to}  # Simplified - should track root
                }
            
            # Send the post
            response = self.client.send_post(**post_data)
            
            logger.info(f"Posted to Bluesky: {response.uri}")
            
            return {
                "success": True,
                "uri": response.uri,
                "cid": response.cid,
                "url": f"https://bsky.app/profile/{self.handle}/post/{response.uri.split('/')[-1]}"
            }
            
        except Exception as e:
            logger.error(f"Error posting to Bluesky: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def post_thread(
        self,
        posts: List[str],
        images: Optional[List[str]] = None,
    ) -> Dict:
        """Post a thread to Bluesky.
        
        Args:
            posts: List of post texts
            images: Optional images for first post
            
        Returns:
            Response dict with thread info
        """
        if not self.client:
            return {"success": False, "error": "Not logged in"}
        
        results = []
        previous_uri = None
        root_uri = None
        
        for i, text in enumerate(posts):
            # Only add images to first post
            post_images = images if i == 0 else None
            
            result = self.post(
                text=text,
                images=post_images,
                reply_to=previous_uri
            )
            
            if result["success"]:
                if i == 0:
                    root_uri = result["uri"]
                previous_uri = result["uri"]
                results.append(result)
            else:
                logger.error(f"Thread interrupted at post {i+1}")
                break
            
            # Small delay between posts
            if i < len(posts) - 1:
                time.sleep(1)
        
        return {
            "success": len(results) == len(posts),
            "posts": results,
            "thread_url": results[0]["url"] if results else None
        }
    
    def repost(self, uri: str) -> Dict:
        """Repost another post.
        
        Args:
            uri: AT URI of the post to repost
            
        Returns:
            Dict with success status and repost info
        """
        try:
            # Parse the URI to get the necessary components
            # URI format: at://did:plc:xxxxx/app.bsky.feed.post/xxxxx
            parts = uri.replace("at://", "").split("/")
            if len(parts) < 3:
                return {"success": False, "error": "Invalid URI format"}
            
            repo = parts[0]
            collection = parts[1]
            rkey = parts[2]
            
            # Create the repost
            repost_record = {
                "$type": "app.bsky.feed.repost",
                "subject": {
                    "uri": uri,
                    "cid": None  # CID would be fetched from the original post
                },
                "createdAt": self.client.get_current_time_iso()
            }
            
            response = self.client.send_post(
                text="",  # Reposts don't have text
                reply_to=None,
                embed=repost_record
            )
            
            logger.info(f"Successfully reposted: {uri}")
            return {
                "success": True,
                "uri": response.uri,
                "reposted_uri": uri
            }
            
        except Exception as e:
            logger.error(f"Error reposting: {e}")
            return {"success": False, "error": str(e)}


class MultiAccountBlueSkyPublisher:
    """Manage multiple Bluesky accounts for PolicyEngine."""
    
    def __init__(self):
        """Initialize multi-account Bluesky publisher."""
        self.accounts = {}
        
        # Load credentials from environment
        account_configs = {
            "policyengine": {
                "handle": os.getenv("BLUESKY_POLICYENGINE_HANDLE"),
                "password": os.getenv("BLUESKY_POLICYENGINE_PASSWORD"),
            },
            "policyengineus": {
                "handle": os.getenv("BLUESKY_POLICYENGINEUS_HANDLE"),
                "password": os.getenv("BLUESKY_POLICYENGINEUS_PASSWORD"),
            },
            "policyengineuk": {
                "handle": os.getenv("BLUESKY_POLICYENGINEUK_HANDLE"),
                "password": os.getenv("BLUESKY_POLICYENGINEUK_PASSWORD"),
            }
        }
        
        # Initialize accounts that have credentials
        for name, config in account_configs.items():
            if config["handle"] and config["password"]:
                try:
                    self.accounts[name] = BlueSkyPublisher(
                        handle=config["handle"],
                        password=config["password"]
                    )
                    logger.info(f"Initialized Bluesky account: {name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize Bluesky {name}: {e}")
    
    def post(self, text: str, account: str = "policyengine", **kwargs) -> Dict:
        """Post to a specific Bluesky account."""
        if account not in self.accounts:
            return {"success": False, "error": f"Account {account} not configured"}
        
        return self.accounts[account].post(text, **kwargs)
    
    def post_thread(self, posts: List[str], account: str = "policyengine", **kwargs) -> Dict:
        """Post a thread to a specific Bluesky account."""
        if account not in self.accounts:
            return {"success": False, "error": f"Account {account} not configured"}
        
        return self.accounts[account].post_thread(posts, **kwargs)
    
    def repost(self, uri: str, from_account: str, to_accounts: List[str]) -> Dict:
        """Repost from one account to other accounts.
        
        Args:
            uri: AT URI of the post to repost
            from_account: Account that posted the original
            to_accounts: List of accounts that should repost
            
        Returns:
            Dict of results by account
        """
        results = {}
        
        for account in to_accounts:
            if account not in self.accounts:
                results[account] = {
                    "success": False,
                    "error": f"Account {account} not configured"
                }
                continue
            
            result = self.accounts[account].repost(uri)
            result["from_account"] = from_account
            results[account] = result
            
            # Small delay between reposts
            time.sleep(1)
        
        return results