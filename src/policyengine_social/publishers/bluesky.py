"""Bluesky publisher for PolicyEngine social media posts."""

import os
import re
import logging
from typing import Dict, List, Optional
from atproto import Client, client_utils
import time
import requests
from bs4 import BeautifulSoup

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
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text.
        
        Args:
            text: Text to extract URLs from
            
        Returns:
            List of URLs found in text
        """
        # Regex pattern for URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def _fetch_url_metadata(self, url: str) -> Dict[str, Optional[str]]:
        """Fetch Open Graph metadata from URL.
        
        Args:
            url: URL to fetch metadata from
            
        Returns:
            Dict with title, description, and image URL
        """
        metadata = {
            'title': None,
            'description': None,
            'image': None
        }
        
        try:
            # Fetch the page
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; PolicyEngine/1.0)'
            })
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try Open Graph tags first
            og_title = soup.find('meta', property='og:title')
            if og_title:
                metadata['title'] = og_title.get('content')
            
            og_description = soup.find('meta', property='og:description')
            if og_description:
                metadata['description'] = og_description.get('content')
            
            og_image = soup.find('meta', property='og:image')
            if og_image:
                metadata['image'] = og_image.get('content')
            
            # Fallback to regular meta tags and title
            if not metadata['title']:
                title_tag = soup.find('title')
                if title_tag:
                    metadata['title'] = title_tag.get_text().strip()
            
            if not metadata['description']:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    metadata['description'] = meta_desc.get('content')
            
            # Ensure we have at least a title
            if not metadata['title']:
                metadata['title'] = url.split('/')[2]  # Use domain as fallback
            
            # Truncate if needed
            if metadata['title'] and len(metadata['title']) > 100:
                metadata['title'] = metadata['title'][:97] + '...'
            
            if metadata['description'] and len(metadata['description']) > 300:
                metadata['description'] = metadata['description'][:297] + '...'
                
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {url}: {e}")
            # Use URL as title fallback
            metadata['title'] = url.split('/')[2] if len(url.split('/')) > 2 else url
        
        return metadata
    
    def post(
        self,
        text: str,
        images: Optional[List[str]] = None,
        reply_to: Optional[Dict] = None,
    ) -> Dict:
        """Post to Bluesky.
        
        Args:
            text: Post text (max 300 characters)
            images: Optional list of image paths
            reply_to: Optional reply reference dict with 'uri' and 'cid'
            
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
            
            # Handle embeds - images take precedence over link previews
            embed = None
            
            # 1. Check for explicit images first
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
                            {"alt": alt, "image": img.model_dump()}
                            for alt, img in zip(image_alts, uploaded_images)
                        ]
                    }
            
            # 2. If no images, check for URLs and create link preview
            elif not embed:
                urls = self._extract_urls(text)
                if urls:
                    # Use the first URL for preview
                    url = urls[0]
                    metadata = self._fetch_url_metadata(url)
                    
                    if metadata['title']:
                        # Create external embed
                        external_data = {
                            "uri": url,
                            "title": metadata['title'],
                            "description": metadata['description'] or ""
                        }
                        
                        # Add thumbnail if available
                        if metadata['image']:
                            try:
                                # Download and upload thumbnail
                                img_response = requests.get(metadata['image'], timeout=10)
                                img_response.raise_for_status()
                                
                                # Upload as blob
                                thumb_upload = self.client.upload_blob(img_response.content)
                                external_data['thumb'] = thumb_upload.blob.model_dump()
                            except Exception as e:
                                logger.warning(f"Failed to upload thumbnail: {e}")
                        
                        embed = {
                            "$type": "app.bsky.embed.external",
                            "external": external_data
                        }
            
            # Create the post
            post_data = {
                "text": post_builder.build_text(),
                "facets": post_builder.build_facets(),
            }
            
            if embed:
                post_data["embed"] = embed
            
            # Send the post with reply_to if provided
            if reply_to:
                # reply_to should be a dict with parent and root URIs and CIDs
                response = self.client.send_post(
                    text=post_builder.build_text(),
                    facets=post_builder.build_facets(),
                    embed=embed,
                    reply_to={
                        "parent": {"uri": reply_to["uri"], "cid": reply_to["cid"]},
                        "root": {"uri": reply_to.get("root_uri", reply_to["uri"]), 
                                "cid": reply_to.get("root_cid", reply_to["cid"])}
                    }
                )
            else:
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
        previous_ref = None
        root_ref = None
        
        for i, text in enumerate(posts):
            # Only add images to first post
            post_images = images if i == 0 else None
            
            # Build reply reference if this is not the first post
            reply_to = None
            if previous_ref:
                reply_to = {
                    "uri": previous_ref["uri"],
                    "cid": previous_ref["cid"],
                    "root_uri": root_ref["uri"],
                    "root_cid": root_ref["cid"]
                }
            
            result = self.post(
                text=text,
                images=post_images,
                reply_to=reply_to
            )
            
            if result["success"]:
                if i == 0:
                    root_ref = {"uri": result["uri"], "cid": result["cid"]}
                previous_ref = {"uri": result["uri"], "cid": result["cid"]}
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
    
    def repost(self, uri: str, cid: str = None) -> Dict:
        """Repost another post.
        
        Args:
            uri: AT URI of the post to repost
            cid: CID of the post to repost (optional, will be fetched if not provided)
            
        Returns:
            Dict with success status and repost info
        """
        try:
            # If CID not provided, we need to fetch it from the original post
            if not cid:
                # Parse URI to get the post details
                # URI format: at://did:plc:xxxxx/app.bsky.feed.post/xxxxx
                parts = uri.replace("at://", "").split("/")
                if len(parts) < 3:
                    return {"success": False, "error": "Invalid URI format"}
                
                did = parts[0]  # The DID of the post author
                rkey = parts[2]  # The post rkey
                
                # Fetch the post to get its CID
                try:
                    post_response = self.client.get_post(
                        post_rkey=rkey,
                        profile_identify=did
                    )
                    cid = post_response.cid  # CID is at the response level
                except Exception as e:
                    logger.warning(f"Could not fetch CID for {uri}: {e}")
                    # CID is required for reposts
                    return {"success": False, "error": f"Could not fetch CID: {e}"}
            
            # Use the built-in repost method
            response = self.client.repost(uri=uri, cid=cid)
            
            logger.info(f"Successfully reposted: {uri}")
            return {
                "success": True,
                "uri": response.uri,
                "cid": response.cid,
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
    
    def repost(self, uri: str, cid: str = None, from_account: str = None, to_accounts: List[str] = None) -> Dict:
        """Repost from one account to other accounts.
        
        Args:
            uri: AT URI of the post to repost
            cid: CID of the post (optional, will be fetched if not provided)
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
            
            result = self.accounts[account].repost(uri, cid)
            if from_account:
                result["from_account"] = from_account
            results[account] = result
            
            # Small delay between reposts
            time.sleep(1)
        
        return results