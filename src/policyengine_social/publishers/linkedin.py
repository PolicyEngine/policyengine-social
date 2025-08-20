"""LinkedIn publisher using Zapier webhooks."""

import logging
from typing import Dict, List, Optional
from .zapier import ZapierPublisher

logger = logging.getLogger(__name__)


class LinkedInPublisher:
    """Publish to LinkedIn via Zapier webhooks."""

    def __init__(self, zapier_webhook_url: str):
        """Initialize LinkedIn publisher with Zapier webhook.

        Args:
            zapier_webhook_url: Zapier webhook URL for LinkedIn posting
        """
        self.zapier = ZapierPublisher(zapier_webhook_url)

    def publish_post(
        self,
        content: str,
        title: Optional[str] = None,
        link: Optional[str] = None,
        images: Optional[List[str]] = None,
    ) -> Dict:
        """Publish a post to LinkedIn.

        Args:
            content: Post content
            title: Optional headline
            link: Optional link to include
            images: Optional list of image URLs

        Returns:
            Response dictionary
        """
        return self.zapier.publish(
            content=content,
            title=title,
            link=link,
            images=images,
            platforms=["linkedin"],
            metadata={"source": "policyengine-social"},
        )

    def publish_article(
        self,
        title: str,
        summary: str,
        link: str,
        cover_image: Optional[str] = None,
    ) -> Dict:
        """Publish an article share to LinkedIn.

        Args:
            title: Article title
            summary: Article summary
            link: Article URL
            cover_image: Optional cover image URL

        Returns:
            Response dictionary
        """
        content = f"{summary}\n\nRead more: {link}"
        images = [cover_image] if cover_image else None

        return self.publish_post(
            content=content,
            title=title,
            link=link,
            images=images,
        )
