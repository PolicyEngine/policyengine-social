#!/usr/bin/env python3
"""Test getting a post to see the CID structure."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from policyengine_social.publishers.bluesky import BlueSkyPublisher

def test_get_post():
    """Test getting a post."""
    
    try:
        publisher = BlueSkyPublisher(
            handle=os.getenv("BLUESKY_POLICYENGINEUS_HANDLE"),
            password=os.getenv("BLUESKY_POLICYENGINEUS_PASSWORD")
        )
        
        # The URI from our latest post
        uri = "at://did:plc:f57y7auibtohzo4b2ckzi6ff/app.bsky.feed.post/3lwxf6tsdya2f"
        parts = uri.replace("at://", "").split("/")
        did = parts[0]
        rkey = parts[2]
        
        print(f"Getting post: {rkey} from {did}")
        
        post_response = publisher.client.get_post(
            post_rkey=rkey,
            profile_identify=did
        )
        
        print(f"Response type: {type(post_response)}")
        print(f"Response attributes: {dir(post_response)}")
        
        if hasattr(post_response, 'value'):
            print(f"Value type: {type(post_response.value)}")
            print(f"Value attributes: {dir(post_response.value)}")
            
        if hasattr(post_response, 'cid'):
            print(f"Direct CID: {post_response.cid}")
            
        # Try to find the CID
        for attr in ['cid', 'uri', 'value']:
            if hasattr(post_response, attr):
                val = getattr(post_response, attr)
                print(f"{attr}: {val}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_post()