#!/usr/bin/env python3
"""Test posting to PolicyEngine X accounts."""

from policyengine_social.publishers.x_multi import MultiAccountXPublisher

# Initialize publisher (will load from .env)
publisher = MultiAccountXPublisher()

# Test 1: Post to @thepolicyengine
print("Testing @thepolicyengine...")
result = publisher.post(
    text="Testing automated posting from policyengine-social! 🚀 This is from our new multi-account posting system.",
    account="thepolicyengine"
)
if result['success']:
    print(f"✅ Success: {result['url']}")
else:
    print(f"❌ Error: {result['error']}")

print("\n" + "="*50 + "\n")

# Test 2: Post to @policyengineus  
print("Testing @policyengineus...")
result = publisher.post(
    text="US-specific test from policyengine-social! 🇺🇸 Automated posting system for PolicyEngine US updates.",
    account="policyengineus"
)
if result['success']:
    print(f"✅ Success: {result['url']}")
else:
    print(f"❌ Error: {result['error']}")

print("\n" + "="*50 + "\n")

# Test 3: Test smart routing
print("Testing smart routing...")
test_text = "New analysis of UK tax policy shows interesting results"
account = publisher.route_by_content(test_text)
print(f"Text: '{test_text}'")
print(f"Would route to: @{account}")