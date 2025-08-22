#!/usr/bin/env python3
"""Test Bluesky repost functionality."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from policyengine_social.publishers.bluesky import MultiAccountBlueSkyPublisher

def test_repost():
    """Test reposting the latest post."""
    
    # The URI and CID from our latest post
    post_uri = "at://did:plc:f57y7auibtohzo4b2ckzi6ff/app.bsky.feed.post/3lwxf6tsdya2f"
    
    try:
        publisher = MultiAccountBlueSkyPublisher()
        
        print("🧪 Testing Bluesky repost functionality...")
        
        # Try to repost from other accounts
        result = publisher.repost(
            uri=post_uri,
            cid=None,  # Let it fetch the CID
            from_account="policyengineus",
            to_accounts=["policyengine", "policyengineuk"]
        )
        
        for account, res in result.items():
            if res['success']:
                print(f"✅ @{account} successfully reposted")
            else:
                print(f"❌ @{account} failed: {res.get('error')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_repost()