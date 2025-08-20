"""Zapier webhook integration for cross-platform posting."""

import json
import logging
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)


class ZapierPublisher:
    """Publisher that uses Zapier webhooks for cross-platform posting."""

    def __init__(self, webhook_url: str):
        """Initialize Zapier publisher.

        Args:
            webhook_url: Zapier webhook catch URL
        """
        self.webhook_url = webhook_url

    def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        link: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Publish content via Zapier webhook.

        Args:
            content: Main text content
            title: Optional title/headline
            images: Optional list of image URLs
            link: Optional link to include
            platforms: Optional list of target platforms
            metadata: Optional additional metadata

        Returns:
            Response from Zapier webhook
        """
        payload = {
            "content": content,
            "title": title,
            "images": images or [],
            "link": link,
            "platforms": platforms or ["linkedin", "twitter"],
            "metadata": metadata or {},
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            logger.info(f"Successfully sent to Zapier webhook")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.text else {},
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send to Zapier: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def publish_thread(
        self,
        posts: List[str],
        platform: str = "twitter",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Publish a thread of posts.

        Args:
            posts: List of post texts
            platform: Target platform
            metadata: Optional additional metadata

        Returns:
            Response from Zapier webhook
        """
        payload = {
            "type": "thread",
            "posts": posts,
            "platform": platform,
            "metadata": metadata or {},
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            logger.info(f"Successfully sent thread to Zapier webhook")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.text else {},
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send thread to Zapier: {e}")
            return {
                "success": False,
                "error": str(e),
            }
