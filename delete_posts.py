#!/usr/bin/env python3
"""Delete the test posts immediately."""

from policyengine_social.publishers.x_multi import MultiAccountXPublisher

# Initialize publisher
publisher = MultiAccountXPublisher()

# Delete from @thepolicyengine
tweet_id_1 = "1957747132963672372"
print(f"Deleting tweet {tweet_id_1} from @thepolicyengine...")
try:
    client = publisher.clients['thepolicyengine']
    response = client.delete_tweet(tweet_id_1)
    print("✅ Deleted from @thepolicyengine")
except Exception as e:
    print(f"❌ Error: {e}")

# Delete from @policyengineus  
tweet_id_2 = "1957747133894787313"
print(f"Deleting tweet {tweet_id_2} from @policyengineus...")
try:
    client = publisher.clients['policyengineus']
    response = client.delete_tweet(tweet_id_2)
    print("✅ Deleted from @policyengineus")
except Exception as e:
    print(f"❌ Error: {e}")