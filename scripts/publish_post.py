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
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policyengine_social.publishers.x_multi import MultiAccountXPublisher
from policyengine_social.publishers.bluesky import MultiAccountBlueSkyPublisher
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
        
        # Handle new format with post_from and repost_from
        if 'post_from' in x_config:
            main_account = x_config['post_from']
            repost_accounts = x_config.get('repost_from', [])
            
            if prod:
                publisher = MultiAccountXPublisher()
                
                # Post from main account
                print(f"\n🐦 Posting to @{main_account}...")
                
                if 'thread' in x_config:
                    result = publisher.post_thread(
                        posts=x_config['thread'],
                        account=main_account,
                        images=x_config.get('images')
                    )
                    if result['success']:
                        print(f"✅ Posted thread: {result['thread_url']}")
                        tweet_id = result['posts'][0]['tweet_id']  # First tweet of thread
                        
                        # Repost from other accounts
                        if repost_accounts:
                            print(f"\n🔄 Reposting from other accounts...")
                            time.sleep(2)  # Wait a bit before reposting
                            repost_results = publisher.repost(
                                tweet_id=tweet_id,
                                from_account=main_account,
                                to_accounts=repost_accounts
                            )
                            for acc, res in repost_results.items():
                                if res['success']:
                                    print(f"  ✅ @{acc} reposted")
                                else:
                                    print(f"  ❌ @{acc} failed: {res.get('error')}")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
                
                elif 'post' in x_config:
                    result = publisher.post(
                        text=x_config['post'],
                        account=main_account,
                        images=x_config.get('images')
                    )
                    if result['success']:
                        print(f"✅ Posted: {result['url']}")
                        tweet_id = result['tweet_id']
                        
                        # Repost from other accounts
                        if repost_accounts:
                            print(f"\n🔄 Reposting from other accounts...")
                            time.sleep(2)  # Wait a bit before reposting
                            repost_results = publisher.repost(
                                tweet_id=tweet_id,
                                from_account=main_account,
                                to_accounts=repost_accounts
                            )
                            for acc, res in repost_results.items():
                                if res['success']:
                                    print(f"  ✅ @{acc} reposted")
                                else:
                                    print(f"  ❌ @{acc} failed: {res.get('error')}")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
            else:
                print("[DRY RUN] X posts:")
                print(f"  Post from @{main_account}:")
                if 'thread' in x_config:
                    for i, tweet in enumerate(x_config['thread'], 1):
                        print(f"    [{i}] {tweet}")
                elif 'post' in x_config:
                    print(f"    {x_config['post']}")
                if repost_accounts:
                    print(f"  Then repost from: {', '.join(['@' + acc for acc in repost_accounts])}")
        
        # Legacy format with accounts list
        elif 'accounts' in x_config:
            if prod:
                publisher = MultiAccountXPublisher()
                
                for account in x_config.get('accounts', []):
                    print(f"\n🐦 Posting to @{account}...")
                    
                    if 'thread' in x_config:
                        result = publisher.post_thread(
                            posts=x_config['thread'],
                            account=account,
                            images=x_config.get('images')
                        )
                        if result['success']:
                            print(f"✅ Posted thread: {result['thread_url']}")
                        else:
                            print(f"❌ Failed: {result.get('error')}")
                    
                    elif 'post' in x_config:
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
                print("[DRY RUN] X posts:")
                for account in x_config.get('accounts', []):
                    print(f"  @{account}:")
                    if 'thread' in x_config:
                        for i, tweet in enumerate(x_config['thread'], 1):
                            print(f"    [{i}] {tweet}")
                    elif 'post' in x_config:
                        print(f"    {x_config['post']}")
    
    # Process Bluesky posts
    if 'bluesky' in post.get('platforms', {}):
        bluesky_config = post['platforms']['bluesky']
        
        # Handle new format with post_from and repost_from
        if 'post_from' in bluesky_config:
            main_account = bluesky_config['post_from']
            repost_accounts = bluesky_config.get('repost_from', [])
            
            if prod:
                publisher = MultiAccountBlueSkyPublisher()
                
                # Post from main account
                print(f"\n🦋 Posting to Bluesky @{main_account}...")
                
                if 'thread' in bluesky_config:
                    result = publisher.post_thread(
                        posts=bluesky_config['thread'],
                        account=main_account,
                        images=bluesky_config.get('images')
                    )
                    if result['success']:
                        print(f"✅ Posted thread: {result['thread_url']}")
                        post_uri = result['posts'][0]['uri']  # First post of thread
                        
                        # Repost from other accounts
                        if repost_accounts:
                            print(f"\n🔄 Reposting from other accounts...")
                            time.sleep(2)  # Wait a bit before reposting
                            repost_results = publisher.repost(
                                uri=post_uri,
                                from_account=main_account,
                                to_accounts=repost_accounts
                            )
                            for acc, res in repost_results.items():
                                if res['success']:
                                    print(f"  ✅ @{acc} reposted")
                                else:
                                    print(f"  ❌ @{acc} failed: {res.get('error')}")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
                
                elif 'post' in bluesky_config:
                    result = publisher.post(
                        text=bluesky_config['post'],
                        account=main_account,
                        images=bluesky_config.get('images')
                    )
                    if result['success']:
                        print(f"✅ Posted: {result['url']}")
                        post_uri = result['uri']
                        
                        # Repost from other accounts
                        if repost_accounts:
                            print(f"\n🔄 Reposting from other accounts...")
                            time.sleep(2)  # Wait a bit before reposting
                            repost_results = publisher.repost(
                                uri=post_uri,
                                from_account=main_account,
                                to_accounts=repost_accounts
                            )
                            for acc, res in repost_results.items():
                                if res['success']:
                                    print(f"  ✅ @{acc} reposted")
                                else:
                                    print(f"  ❌ @{acc} failed: {res.get('error')}")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
            else:
                print("\n[DRY RUN] Bluesky posts:")
                print(f"  Post from @{main_account}:")
                if 'thread' in bluesky_config:
                    for i, post_text in enumerate(bluesky_config['thread'], 1):
                        print(f"    [{i}] {post_text}")
                elif 'post' in bluesky_config:
                    print(f"    {bluesky_config['post']}")
                if repost_accounts:
                    print(f"  Then repost from: {', '.join(['@' + acc for acc in repost_accounts])}")
        
        # Legacy format with accounts list
        elif 'accounts' in bluesky_config:
            if prod:
                publisher = MultiAccountBlueSkyPublisher()
                
                for account in bluesky_config.get('accounts', []):
                    print(f"\n🦋 Posting to Bluesky @{account}...")
                    
                    if 'thread' in bluesky_config:
                        result = publisher.post_thread(
                            posts=bluesky_config['thread'],
                            account=account,
                            images=bluesky_config.get('images')
                        )
                        if result['success']:
                            print(f"✅ Posted thread: {result['thread_url']}")
                        else:
                            print(f"❌ Failed: {result.get('error')}")
                    
                    elif 'post' in bluesky_config:
                        result = publisher.post(
                            text=bluesky_config['post'],
                            account=account,
                            images=bluesky_config.get('images')
                        )
                        if result['success']:
                            print(f"✅ Posted: {result['url']}")
                        else:
                            print(f"❌ Failed: {result.get('error')}")
            else:
                print("\n[DRY RUN] Bluesky posts:")
                for account in bluesky_config.get('accounts', []):
                    print(f"  @{account}:")
                    if 'thread' in bluesky_config:
                        for i, post_text in enumerate(bluesky_config['thread'], 1):
                            print(f"    [{i}] {post_text}")
                    elif 'post' in bluesky_config:
                        print(f"    {bluesky_config['post']}")
    
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