#!/usr/bin/env python3
"""
Publish a validated post from YAML file.
This should ONLY be run by GitHub Actions after PR approval.
"""

import sys
import yaml
import argparse
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policyengine_social.publishers.x_multi import MultiAccountXPublisher
from policyengine_social.publishers.zapier import ZapierPublisher


def publish_post(filepath, prod=False):
    """Publish a post from YAML file.
    
    Args:
        filepath: Path to post YAML file
        prod: If True, actually post. If False, dry run only.
    """
    with open(filepath, 'r') as f:
        post = yaml.safe_load(f)
    
    print(f"\n{'='*50}")
    print(f"📱 Processing: {post.get('title', 'Untitled')}")
    print(f"{'='*50}\n")
    
    results = []
    
    # Process X posts
    if 'x' in post.get('platforms', {}):
        x_config = post['platforms']['x']
        
        if prod:
            publisher = MultiAccountXPublisher()
            
            for account in x_config.get('accounts', []):
                print(f"\n🐦 Posting to @{account}...")
                
                if 'thread' in x_config:
                    # Post as thread
                    if prod:
                        result = publisher.post_thread(
                            posts=x_config['thread'],
                            account=account,
                            images=x_config.get('images')
                        )
                        if result['success']:
                            print(f"✅ Posted thread: {result['thread_url']}")
                        else:
                            print(f"❌ Failed: {result.get('error')}")
                    else:
                        print("[DRY RUN] Would post thread:")
                        for i, tweet in enumerate(x_config['thread'], 1):
                            print(f"  [{i}] {tweet}")
                
                elif 'post' in x_config:
                    # Single post
                    if prod:
                        result = publisher.post(
                            text=x_config['post'],
                            account=account,
                            images=x_config.get('images')
                        )
                        if result['success']:
                            print(f"✅ Posted: {result['url']}")
                        else:
                            print(f"❌ Failed: {result.get('error')}")
                    else:
                        print(f"[DRY RUN] Would post: {x_config['post']}")
        else:
            print("[DRY RUN] X posts:")
            for account in x_config.get('accounts', []):
                print(f"  @{account}:")
                if 'thread' in x_config:
                    for i, tweet in enumerate(x_config['thread'], 1):
                        print(f"    [{i}] {tweet}")
                elif 'post' in x_config:
                    print(f"    {x_config['post']}")
    
    # Process LinkedIn posts
    if 'linkedin' in post.get('platforms', {}):
        linkedin_config = post['platforms']['linkedin']
        
        if prod and os.getenv('ZAPIER_LINKEDIN_WEBHOOK'):
            print(f"\n💼 Posting to LinkedIn...")
            zapier = ZapierPublisher(os.getenv('ZAPIER_LINKEDIN_WEBHOOK'))
            result = zapier.publish(
                content=linkedin_config['content'],
                link=linkedin_config.get('article_url')
            )
            if result['success']:
                print(f"✅ Sent to LinkedIn via Zapier")
            else:
                print(f"❌ Failed: {result.get('error')}")
        else:
            print(f"\n[DRY RUN] LinkedIn post:")
            print(f"  {linkedin_config['content'][:200]}...")
    
    print(f"\n{'='*50}")
    print(f"📱 Completed: {post.get('title', 'Untitled')}")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Publish social media post")
    parser.add_argument('file', help='Path to post YAML file')
    parser.add_argument('--prod', action='store_true', 
                       help='Actually post (default is dry run)')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    if args.prod:
        print("⚠️  PRODUCTION MODE - Posts will be published!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    else:
        print("🔍 DRY RUN MODE - No posts will be published\n")
    
    publish_post(args.file, prod=args.prod)


if __name__ == "__main__":
    main()