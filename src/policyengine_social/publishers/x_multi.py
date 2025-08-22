"""Multi-account X (Twitter) publisher for PolicyEngine."""

import os
import yaml
import tweepy
import logging
from pathlib import Path
from typing import Dict, List, Optional, Literal
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

AccountName = Literal["thepolicyengine", "policyengineus", "policyengineuk"]


class MultiAccountXPublisher:
    """Manages posting to multiple PolicyEngine X accounts."""

    def __init__(self, config_path: str = None, use_env: bool = True):
        """Initialize multi-account publisher.

        Args:
            config_path: Path to x_accounts.yaml config file
            use_env: Whether to use environment variables (default: True)
        """
        if use_env:
            # Load from environment variables
            self.config = self._load_from_env()
        else:
            # Load from config file
            if config_path is None:
                config_path = (
                    Path(__file__).parent.parent.parent.parent
                    / "config"
                    / "x_accounts.yaml"
                )

            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)

        self.clients = {}
        self.apis = {}  # For media upload (v1.1 API)

        # Initialize clients for each account
        for account_name, creds in self.config["accounts"].items():
            self.clients[account_name] = tweepy.Client(
                consumer_key=creds["api_key"],
                consumer_secret=creds["api_secret"],
                access_token=creds["access_token"],
                access_token_secret=creds["access_token_secret"],
            )

            # Also create v1.1 API client for media uploads
            auth = tweepy.OAuth1UserHandler(
                creds["api_key"],
                creds["api_secret"],
                creds["access_token"],
                creds["access_token_secret"],
            )
            self.apis[account_name] = tweepy.API(auth)

    def _load_from_env(self) -> Dict:
        """Load configuration from environment variables."""
        config = {
            "accounts": {},
            "settings": {
                "default_account": "thepolicyengine",
                "thread_delay_seconds": 2,
                "max_retries": 3,
            },
            "routing": {
                "by_tag": {
                    "us": "policyengineus",
                    "uk": "policyengineuk",
                    "general": "thepolicyengine",
                }
            },
        }

        # Account prefixes
        account_prefixes = {
            "thepolicyengine": "X_THEPOLICYENGINE",
            "policyengineus": "X_POLICYENGINEUS",
            "policyengineuk": "X_POLICYENGINEUK",
        }

        for account_name, prefix in account_prefixes.items():
            api_key = os.getenv(f"{prefix}_API_KEY")
            api_secret = os.getenv(f"{prefix}_API_SECRET")
            access_token = os.getenv(f"{prefix}_ACCESS_TOKEN")
            access_token_secret = os.getenv(f"{prefix}_ACCESS_TOKEN_SECRET")

            if api_key and api_secret and access_token and access_token_secret:
                config["accounts"][account_name] = {
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "access_token": access_token,
                    "access_token_secret": access_token_secret,
                }

        return config

    def post(
        self,
        text: str,
        account: AccountName = None,
        images: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict:
        """Post to a specific account.

        Args:
            text: Post text
            account: Account name (defaults to config default)
            images: Optional list of image paths
            reply_to: Optional tweet ID to reply to

        Returns:
            Response dict with tweet ID and URL
        """
        if account is None:
            account = self.config["settings"]["default_account"]

        client = self.clients.get(account)
        if not client:
            raise ValueError(f"Unknown account: {account}")

        try:
            # Upload images if provided
            media_ids = None
            if images:
                media_ids = self._upload_media(account, images)

            # Post tweet
            if reply_to:
                response = client.create_tweet(
                    text=text, media_ids=media_ids, in_reply_to_tweet_id=reply_to
                )
            else:
                response = client.create_tweet(text=text, media_ids=media_ids)

            tweet_id = response.data["id"]

            logger.info(f"Posted to @{account}: {tweet_id}")

            return {
                "success": True,
                "account": account,
                "tweet_id": tweet_id,
                "url": f"https://x.com/{account}/status/{tweet_id}",
            }

        except Exception as e:
            logger.error(f"Error posting to @{account}: {e}")
            return {"success": False, "account": account, "error": str(e)}

    def post_thread(
        self,
        posts: List[str],
        account: AccountName = None,
        images: Optional[List[str]] = None,
    ) -> Dict:
        """Post a thread to a specific account.

        Args:
            posts: List of post texts
            account: Account name
            images: Optional images for first post

        Returns:
            Response dict with thread info
        """
        if account is None:
            account = self.config["settings"]["default_account"]

        results = []
        previous_id = None

        for i, text in enumerate(posts):
            # Only add images to first post
            post_images = images if i == 0 else None

            result = self.post(
                text=text, account=account, images=post_images, reply_to=previous_id
            )

            if result["success"]:
                previous_id = result["tweet_id"]
                results.append(result)
            else:
                logger.error(f"Thread interrupted at post {i+1}")
                break

            # Delay between posts
            if i < len(posts) - 1:
                time.sleep(self.config["settings"]["thread_delay_seconds"])

        return {
            "success": len(results) == len(posts),
            "account": account,
            "posts": results,
            "thread_url": results[0]["url"] if results else None,
        }

    def post_to_all(
        self,
        text: str,
        exclude: Optional[List[str]] = None,
    ) -> Dict:
        """Post the same content to all accounts.

        Args:
            text: Post text
            exclude: Optional list of accounts to skip

        Returns:
            Dict of results by account
        """
        exclude = exclude or []
        results = {}

        for account in self.config["accounts"].keys():
            if account not in exclude:
                results[account] = self.post(text=text, account=account)
                # Small delay between accounts
                time.sleep(1)

        return results

    def retweet(
        self,
        tweet_id: str,
        from_account: AccountName,
        to_accounts: List[AccountName],
    ) -> Dict:
        """Retweet a post from one account to other accounts.
        
        Args:
            tweet_id: ID of the tweet to retweet
            from_account: Account that posted the original tweet
            to_accounts: List of accounts that should retweet
            
        Returns:
            Dict of results by account
        """
        results = {}
        
        for account in to_accounts:
            if account not in self.clients:
                results[account] = {
                    "success": False, 
                    "error": f"Account {account} not configured"
                }
                continue
                
            try:
                client = self.clients[account]
                # Retweet using the X API
                response = client.retweet(tweet_id)
                results[account] = {
                    "success": True,
                    "account": account,
                    "retweeted_id": tweet_id,
                    "from_account": from_account,
                }
                logger.info(f"@{account} retweeted {tweet_id} from @{from_account}")
                
                # Small delay between retweets
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error retweeting from @{account}: {e}")
                results[account] = {
                    "success": False,
                    "account": account,
                    "error": str(e)
                }
                
        return results

    def route_by_content(
        self,
        text: str,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> AccountName:
        """Determine which account should post based on content.

        Args:
            text: Post text
            tags: Optional content tags
            category: Optional content category

        Returns:
            Account name to use
        """
        routing = self.config.get("routing", {})

        # Check category first
        if category and "by_category" in routing:
            if category in routing["by_category"]:
                return routing["by_category"][category]

        # Check tags
        if tags and "by_tag" in routing:
            for tag in tags:
                if tag in routing["by_tag"]:
                    return routing["by_tag"][tag]

        # Check content for country mentions
        text_lower = text.lower()
        if any(
            term in text_lower for term in ["united states", "u.s.", " us ", "america"]
        ):
            return "policyengineus"
        elif any(
            term in text_lower for term in ["united kingdom", "u.k.", " uk ", "britain"]
        ):
            return "policyengineuk"

        # Default
        return self.config["settings"]["default_account"]

    def _upload_media(self, account: str, image_paths: List[str]) -> List[str]:
        """Upload media files for a specific account.

        Args:
            account: Account name
            image_paths: List of image file paths

        Returns:
            List of media IDs
        """
        api = self.apis[account]
        media_ids = []

        for path in image_paths:
            if os.path.exists(path):
                media = api.media_upload(path)
                media_ids.append(media.media_id_string)
                logger.info(f"Uploaded media for @{account}: {path}")

        return media_ids if media_ids else None
