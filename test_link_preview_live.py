#!/usr/bin/env python3
"""Test Bluesky link preview with a real post."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from policyengine_social.publishers.bluesky import BlueSkyPublisher

def test_link_preview():
    """Test posting with automatic link preview."""
    
    try:
        publisher = BlueSkyPublisher(
            handle=os.getenv("BLUESKY_POLICYENGINEUS_HANDLE"),
            password=os.getenv("BLUESKY_POLICYENGINEUS_PASSWORD")
        )
        
        print("🧪 Testing Bluesky post with link preview...")
        
        # Post with the NSF grant URL
        result = publisher.post(
            text="Testing link preview: Our NSF POSE Phase I grant announcement https://policyengine.org/us/research/nsf-pose-phase-1-grant"
        )
        
        if result['success']:
            print(f"✅ Successfully posted with link preview: {result['url']}")
            print(f"   URI: {result['uri']}")
            print("\n   Check the post to see if the link preview card appears!")
        else:
            print(f"❌ Failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_link_preview()