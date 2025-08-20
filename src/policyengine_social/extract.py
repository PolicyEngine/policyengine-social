#!/usr/bin/env python3
"""
Extract and process images from PolicyEngine blog posts.
"""

import re
import requests
from pathlib import Path
from typing import List, Dict
import yaml
from PIL import Image
import subprocess


class BlogImageExtractor:
    def __init__(self, blog_slug: str):
        self.slug = blog_slug
        self.app_repo = (
            "https://raw.githubusercontent.com/PolicyEngine/policyengine-app/master"
        )
        self.cache_dir = Path("assets/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_images(self) -> Dict:
        """Extract all images from a blog post."""
        images = {}

        # 1. Get cover image from posts.json
        posts_json = self._fetch_posts_json()
        for post in posts_json:
            if post["filename"].replace(".md", "") == self.slug:
                cover_image = post.get("image")
                if cover_image:
                    images["cover"] = {
                        "id": "cover",
                        "filename": cover_image,
                        "url": f"{self.app_repo}/src/images/posts/{cover_image}",
                        "alt": f"Cover image for {post['title']}",
                        "type": "hero",
                    }
                break

        # 2. Parse markdown for inline images
        markdown_content = self._fetch_blog_markdown()

        # Find all markdown images: ![alt](url)
        md_images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", markdown_content)
        for i, (alt_text, img_path) in enumerate(md_images, 1):
            images[f"inline_{i}"] = {
                "id": f"inline_{i}",
                "filename": Path(img_path).name,
                "url": self._resolve_image_url(img_path),
                "alt": alt_text or f"Image {i} from article",
                "type": "supporting",
            }

        # 3. Find any HTML images
        html_images = re.findall(r'<img[^>]+src="([^"]+)"[^>]*>', markdown_content)
        for i, img_src in enumerate(html_images, 1):
            images[f"html_{i}"] = {
                "id": f"html_{i}",
                "filename": Path(img_src).name,
                "url": self._resolve_image_url(img_src),
                "alt": f"Embedded image {i}",
                "type": "embedded",
            }

        return images

    def _fetch_posts_json(self) -> List[Dict]:
        """Fetch posts.json from the app repo."""
        url = f"{self.app_repo}/src/posts/posts.json"
        response = requests.get(url)
        return response.json()

    def _fetch_blog_markdown(self) -> str:
        """Fetch the blog post markdown."""
        url = f"{self.app_repo}/src/posts/articles/{self.slug}.md"
        response = requests.get(url)
        return response.text

    def _resolve_image_url(self, path: str) -> str:
        """Resolve relative image paths to full URLs."""
        if path.startswith("http"):
            return path
        if path.startswith("/"):
            return f"{self.app_repo}{path}"
        return f"{self.app_repo}/src/posts/articles/{path}"

    def download_image(self, image_info: Dict) -> Path:
        """Download and cache an image locally."""
        cache_path = self.cache_dir / image_info["filename"]

        if not cache_path.exists():
            response = requests.get(image_info["url"])
            if response.status_code == 200:
                cache_path.write_bytes(response.content)
                print(f"✓ Downloaded: {image_info['filename']}")
            else:
                print(f"✗ Failed to download: {image_info['url']}")
                return None
        else:
            print(f"↺ Using cached: {image_info['filename']}")

        return cache_path

    def optimize_for_platform(self, image_path: Path, platform: str) -> Path:
        """Optimize image for specific platform requirements."""
        img = Image.open(image_path)
        optimized_dir = Path("assets/optimized") / platform
        optimized_dir.mkdir(parents=True, exist_ok=True)

        output_path = optimized_dir / image_path.name

        if platform == "x":
            # X/Twitter: Max 5MB, prefer 16:9 for in-stream
            img.thumbnail((1200, 675), Image.Resampling.LANCZOS)
            img.save(output_path, optimize=True, quality=85)

        elif platform == "linkedin":
            # LinkedIn: 1200x627 for best results
            img.thumbnail((1200, 627), Image.Resampling.LANCZOS)
            img.save(output_path, optimize=True, quality=90)

        print(f"⚡ Optimized for {platform}: {output_path}")
        return output_path

    def capture_screenshot(self, url: str, output_name: str) -> Path:
        """Capture screenshot of a webpage (requires playwright)."""
        output_path = self.cache_dir / f"{output_name}.png"

        # Using playwright CLI (install: pip install playwright && playwright install)
        cmd = [
            "playwright",
            "screenshot",
            "--wait-for-timeout=3000",
            "--viewport-size=1200,630",
            url,
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"📸 Captured screenshot: {output_name}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"✗ Screenshot failed: {e}")
            return None

    def auto_select_images(self, images: Dict, platform: str) -> List[str]:
        """Intelligently select images for social media post."""
        selected = []

        # Always include cover if available
        if "cover" in images:
            selected.append("cover")

        # Platform-specific selection
        if platform == "x":
            # For X threads, distribute images across tweets
            # Max 4 images per tweet
            supporting = [k for k, v in images.items() if v["type"] == "supporting"][:3]
            selected.extend(supporting)

        elif platform == "linkedin":
            # LinkedIn: Usually just hero image
            # Or create carousel from multiple charts
            if len(images) > 2:
                # Suggest carousel
                selected = list(images.keys())[:5]  # Max 5 for carousel

        return selected


def main():
    """Example usage."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument(
        "--download", action="store_true", help="Download images locally"
    )
    parser.add_argument(
        "--optimize", choices=["x", "linkedin"], help="Optimize for platform"
    )
    parser.add_argument("--screenshot", help="URL to screenshot")

    args = parser.parse_args()

    extractor = BlogImageExtractor(args.slug)
    images = extractor.extract_images()

    print(f"\n📎 Found {len(images)} images in blog post:")
    for img_id, info in images.items():
        print(f"  - {img_id}: {info['filename']} ({info['type']})")

    if args.download:
        for img_info in images.values():
            extractor.download_image(img_info)

    if args.optimize and images:
        # Optimize cover image for platform
        if "cover" in images:
            cover_path = extractor.download_image(images["cover"])
            if cover_path:
                extractor.optimize_for_platform(cover_path, args.optimize)

    if args.screenshot:
        extractor.capture_screenshot(args.screenshot, f"{args.slug}-screenshot")

    # Save image manifest
    manifest_path = Path(f"posts/queue/{args.slug}-images.yaml")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        yaml.dump({"images": images}, f)
    print(f"\n✅ Saved image manifest: {manifest_path}")


if __name__ == "__main__":
    main()
