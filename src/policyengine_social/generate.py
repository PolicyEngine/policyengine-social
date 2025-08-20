#!/usr/bin/env python3
"""
Generate social media posts from PolicyEngine blog articles.
"""

import argparse
import yaml
import requests
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List


class SocialPostGenerator:
    def __init__(self, slug: str, title: str = None):
        self.slug = slug
        self.title = title
        self.blog_url = f"https://policyengine.org/us/blog/{slug}"
        self.content = self.fetch_blog_content()

    def fetch_blog_content(self) -> Dict:
        """Fetch blog content from PolicyEngine app repo."""
        # In production, this would fetch from the actual blog
        # For now, we'll use a template approach
        return {
            "title": self.title or self.slug.replace("-", " ").title(),
            "description": "Blog post description",
            "content": "Blog post content...",
            "url": self.blog_url,
        }

    def generate_x_thread(self) -> List[str]:
        """Generate X/Twitter thread from blog content."""
        thread = []

        # Tweet 1: Hook with key announcement
        if "grant" in self.slug.lower():
            thread.append(
                f"🎉 {self.content['title']}\n\n"
                f"We're excited to share this important update about PolicyEngine's future.\n\n"
                f"🧵 Thread:"
            )
        else:
            thread.append(
                f"📊 New from PolicyEngine: {self.content['title']}\n\n"
                f"Here's what you need to know 🧵"
            )

        # Tweet 2: Key points
        thread.append(
            "Key highlights:\n"
            "• Point 1 from the article\n"
            "• Point 2 from the article\n"
            "• Point 3 from the article"
        )

        # Tweet 3: Call to action
        thread.append(
            f"Read the full article for more details:\n"
            f"{self.blog_url}\n\n"
            f"Questions? Let us know below 👇"
        )

        return thread

    def generate_linkedin_post(self) -> str:
        """Generate LinkedIn post from blog content."""
        post = f"""📊 {self.content['title']}

We're pleased to share our latest article exploring [topic description].

Key takeaways:
• Important finding or announcement
• Supporting detail or impact
• Call to action or next steps

This [article/analysis/announcement] demonstrates PolicyEngine's commitment to democratizing policy analysis and making economic modeling accessible to all.

Read the full article: {self.blog_url}

What are your thoughts on [relevant question]? We'd love to hear your perspective in the comments.

#PolicyAnalysis #EconomicModeling #OpenSource #PublicPolicy #DataScience"""

        return post

    def generate_post_yaml(self) -> Dict:
        """Generate the complete YAML structure for the post."""
        # Schedule for tomorrow at 10 AM ET
        tomorrow = datetime.now() + timedelta(days=1)
        publish_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Extract images from blog
        from policyengine_social.extract import BlogImageExtractor

        extractor = BlogImageExtractor(self.slug)
        images = extractor.extract_images()

        # Auto-select images for each platform
        x_images = extractor.auto_select_images(images, "x")
        linkedin_images = extractor.auto_select_images(images, "linkedin")

        return {
            "title": self.content["title"],
            "source": f"blog/{self.slug}",
            "url": self.blog_url,
            "publish_at": publish_time.isoformat(),
            "status": "draft",
            "images": images,  # All available images
            "platforms": {
                "x": {
                    "thread": self.generate_x_thread(),
                    "media": x_images,  # Selected image IDs
                    "hashtags": ["PolicyEngine", "PolicyAnalysis"],
                },
                "linkedin": {
                    "text": self.generate_linkedin_post(),
                    "media": linkedin_images[:1],  # Usually just one
                    "visibility": "public",
                },
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator_version": "1.0.0",
                "auto_selected_images": True,
            },
        }


def main():
    parser = argparse.ArgumentParser(
        description="Generate social media posts from blog"
    )
    parser.add_argument("--slug", required=True, help="Blog post slug")
    parser.add_argument("--title", help="Blog post title")
    parser.add_argument("--output", required=True, help="Output YAML file path")

    args = parser.parse_args()

    # Generate the post
    generator = SocialPostGenerator(args.slug, args.title)
    post_data = generator.generate_post_yaml()

    # Save to YAML file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(post_data, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Generated social post: {output_path}")


if __name__ == "__main__":
    main()
