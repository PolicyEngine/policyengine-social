#!/usr/bin/env python3
"""Validate a social media post YAML file."""

import sys
import yaml
from pathlib import Path


def validate_post(filepath):
    """Validate a post YAML file."""
    with open(filepath, 'r') as f:
        post = yaml.safe_load(f)
    
    errors = []
    
    # Check required fields
    required = ['title', 'platforms']
    for field in required:
        if field not in post:
            errors.append(f"Missing required field: {field}")
    
    # Validate platforms
    if 'platforms' in post:
        if 'x' in post['platforms']:
            x_config = post['platforms']['x']
            
            # Check accounts
            if 'accounts' not in x_config:
                errors.append("X platform missing 'accounts' field")
            else:
                valid_accounts = ['thepolicyengine', 'policyengineus', 'policyengineuk']
                for account in x_config['accounts']:
                    if account not in valid_accounts:
                        errors.append(f"Invalid X account: {account}")
            
            # Check content
            if 'thread' not in x_config and 'post' not in x_config:
                errors.append("X platform needs either 'thread' or 'post' field")
            
            # Check tweet length
            if 'thread' in x_config:
                for i, tweet in enumerate(x_config['thread']):
                    length = len(tweet)
                    if length > 280:
                        errors.append(f"Tweet {i+1} is too long: {length} chars")
                    else:
                        print(f"  ✓ Tweet {i+1}: {length}/280 chars")
            
            if 'post' in x_config and len(x_config['post']) > 280:
                errors.append(f"Post is too long: {len(x_config['post'])} chars")
        
        if 'linkedin' in post['platforms']:
            linkedin_config = post['platforms']['linkedin']
            if 'content' not in linkedin_config:
                errors.append("LinkedIn platform missing 'content' field")
    
    # Report results
    if errors:
        print(f"❌ Validation failed for {filepath}:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print(f"✅ {filepath} is valid")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_post.py <post.yaml>")
        sys.exit(1)
    
    validate_post(sys.argv[1])