#!/usr/bin/env python3
"""CLI for PolicyEngine social media posting."""

import argparse
import yaml
from pathlib import Path
from typing import Optional
from .publishers.x_multi import MultiAccountXPublisher
from .publishers.zapier import ZapierPublisher
from .generate import SocialPostGenerator
from .extract import BlogImageExtractor


def post_to_x(args):
    """Post to X accounts."""
    publisher = MultiAccountXPublisher(args.config)

    if args.thread:
        # Read thread from file or stdin
        if args.thread == "-":
            import sys

            posts = [line.strip() for line in sys.stdin if line.strip()]
        else:
            with open(args.thread, "r") as f:
                posts = [line.strip() for line in f if line.strip()]

        result = publisher.post_thread(
            posts=posts, account=args.account, images=args.images
        )
    else:
        # Single post
        result = publisher.post(
            text=args.text, account=args.account, images=args.images
        )

    if result["success"]:
        print(f"✅ Posted successfully!")
        print(f"📱 View at: {result.get('url') or result.get('thread_url')}")
    else:
        print(f"❌ Error: {result.get('error')}")

    return result["success"]


def generate_posts(args):
    """Generate social media posts from blog content."""
    generator = SocialPostGenerator(args.url or args.file)

    if args.platform == "x":
        posts = generator.generate_x_thread(max_posts=args.max_posts)
        print("Generated X thread:")
        for i, post in enumerate(posts, 1):
            print(f"\n[{i}/{len(posts)}]")
            print(post)
    elif args.platform == "linkedin":
        post = generator.generate_linkedin_post()
        print("Generated LinkedIn post:")
        print(post)

    if args.output:
        # Save to file
        output = {
            "platform": args.platform,
            "posts": posts if args.platform == "x" else [post],
            "source": args.url or args.file,
        }
        with open(args.output, "w") as f:
            yaml.dump(output, f)
        print(f"\n💾 Saved to: {args.output}")


def extract_images(args):
    """Extract images from blog post."""
    extractor = BlogImageExtractor(args.url or args.file)
    images = extractor.extract_images()

    print(f"Found {len(images)} images:")
    for img in images:
        print(f"  - {img['type']}: {img['filename']}")
        if args.download:
            path = extractor.download_image(img)
            if path:
                print(f"    Downloaded to: {path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="PolicyEngine social media automation")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Post to X command
    post_x = subparsers.add_parser("post-x", help="Post to X (Twitter)")
    post_x.add_argument("text", nargs="?", help="Text to post")
    post_x.add_argument(
        "--account",
        "-a",
        choices=["thepolicyengine", "policyengineus", "policyengineuk"],
        help="Account to post from",
    )
    post_x.add_argument(
        "--thread", "-t", help="Post thread from file (use - for stdin)"
    )
    post_x.add_argument("--images", "-i", nargs="+", help="Image paths to attach")
    post_x.add_argument("--config", "-c", help="Config file path")

    # Generate posts command
    gen = subparsers.add_parser("generate", help="Generate posts from blog")
    gen.add_argument("--url", "-u", help="Blog post URL")
    gen.add_argument("--file", "-f", help="Blog post file")
    gen.add_argument(
        "--platform",
        "-p",
        choices=["x", "linkedin", "all"],
        default="all",
        help="Platform to generate for",
    )
    gen.add_argument("--max-posts", type=int, default=10, help="Max posts in thread")
    gen.add_argument("--output", "-o", help="Save to file")

    # Extract images command
    extract = subparsers.add_parser("extract", help="Extract images from blog")
    extract.add_argument("--url", "-u", help="Blog post URL")
    extract.add_argument("--file", "-f", help="Blog post file")
    extract.add_argument(
        "--download", "-d", action="store_true", help="Download images"
    )

    # Batch post command
    batch = subparsers.add_parser("batch", help="Post to all accounts")
    batch.add_argument("text", help="Text to post")
    batch.add_argument("--exclude", "-e", nargs="+", help="Accounts to exclude")
    batch.add_argument("--config", "-c", help="Config file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "post-x":
        return 0 if post_to_x(args) else 1
    elif args.command == "generate":
        generate_posts(args)
        return 0
    elif args.command == "extract":
        extract_images(args)
        return 0
    elif args.command == "batch":
        publisher = MultiAccountXPublisher(args.config)
        results = publisher.post_to_all(args.text, exclude=args.exclude)
        success = all(r["success"] for r in results.values())

        for account, result in results.items():
            if result["success"]:
                print(f"✅ @{account}: {result['url']}")
            else:
                print(f"❌ @{account}: {result.get('error')}")

        return 0 if success else 1

    return 0


if __name__ == "__main__":
    exit(main())
