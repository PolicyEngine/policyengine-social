# PolicyEngine Social Media Automation - AI Development Guidelines

## CRITICAL RULES - NEVER VIOLATE THESE

### 🚨 NEVER POST WITHOUT EXPLICIT PERMISSION
- **NEVER run any code that posts to social media without explicit user permission**
- **NEVER test posting functionality with actual posts**
- **ALWAYS use dry-run mode or print statements for testing**
- **ALWAYS ask "May I post this?" before executing any posting code**
- If testing is needed, create scripts for the USER to run, don't run them yourself

### ⚠️ NEVER DELETE WITHOUT CAREFUL REVIEW
- **ALWAYS READ THE FULL CONTENT** of posts before deleting - don't just scan for keywords
- **CHECK POST DATES** - Never delete historical content (older than 24 hours) without explicit confirmation
- **UNDERSTAND CONTEXT** - Replies to legitimate posts are valuable engagement, not test content
- **SHOW FULL LIST** for review before any batch deletion
- **BE CONSERVATIVE** - When in doubt, DON'T DELETE
- **NEVER assume replies are test content** - They are usually legitimate engagement

### Example of what NOT to do:
```python
# ❌ NEVER DO THIS WITHOUT PERMISSION
publisher.post("Test message")  # DO NOT RUN

# ❌ NEVER DELETE WITHOUT READING
for post in posts:
    if "test" in post.text.lower():  # NO! This could delete legitimate content!
        client.delete_post(post.uri)

# ❌ NEVER DELETE OLD CONTENT WITHOUT EXPLICIT CONFIRMATION
if post.created_at < datetime.now() - timedelta(days=1):
    client.delete_post(post.uri)  # NO! This is historical content!
```

### Example of safe testing:
```python
# ✅ Safe - just prints what would be posted
print(f"Would post: {message}")
print(f"To account: @{account}")
# Don't actually call publisher.post()

# ✅ Safe deletion review
for post in posts_to_maybe_delete:
    print(f"Date: {post.created_at}")
    print(f"Content: {post.text}")  # READ IT!
    print(f"Is Reply: {post.is_reply}")
    print("---")
print(f"\nWould delete {len(posts_to_maybe_delete)} posts")
# Get explicit confirmation before any deletion
```

## Repository Overview

This repository handles automated social media posting for PolicyEngine across multiple platforms:
- X (Twitter): @thepolicyengine, @policyengineus, @policyengineuk
- Bluesky: @policyengine.org, @us.policyengine.org, @uk.policyengine.org
- LinkedIn: Via Zapier webhooks

## Content Preservation Guidelines

### Types of Content to ALWAYS PRESERVE:
- Webinar announcements and recordings
- Research reports and analysis
- Grant announcements (except confirmed test duplicates from same day)
- Job postings and recruitment
- Community engagement and replies to posts
- Newsletter announcements
- Policy analysis results
- Historical posts (anything older than 24 hours)
- Replies to legitimate posts (these are engagement, not tests!)

### Content that MAY be test content (still requires confirmation):
- Posts explicitly containing "test" or "testing" AND created in last 24 hours
- Duplicate posts from the same day
- Posts with obvious placeholder content like "test123"

## Environment Setup

### Required Environment Variables
The system uses environment variables stored in `.env` (never commit this file!):
- `X_THEPOLICYENGINE_*` - Credentials for @thepolicyengine
- `X_POLICYENGINEUS_*` - Credentials for @policyengineus  
- `X_POLICYENGINEUK_*` - Credentials for @policyengineuk
- `ZAPIER_*` - Webhook URLs for LinkedIn posting

### Virtual Environment
Always use the virtual environment:
```bash
source venv/bin/activate
```

## Testing Guidelines

### Safe Testing Practices
1. **Create test scripts for the user to run** - Don't run them yourself
2. **Use print statements** to show what would be posted
3. **Add --dry-run flags** to CLI commands
4. **Mock API calls** in unit tests

### Before Any Real Post
Always get explicit confirmation:
```
"I'm ready to post the following:
Text: [exact text]
Account: [account name]
May I proceed with posting?"
```

## Code Patterns

### Multi-Account X Publisher
- Automatically loads credentials from environment variables
- Routes content to appropriate account based on tags/content
- Supports threads and media uploads

### Smart Routing
- US content → @policyengineus
- UK content → @policyengineuk
- General content → @thepolicyengine

## Common Commands

```bash
# Install dependencies
pip install -e .

# CLI usage (ONLY with user permission)
pe-social post-x "message" --account thepolicyengine --dry-run

# Generate posts from blog
pe-social generate --url https://policyengine.org/us/research/post-name
```

## GitHub Actions

The repository includes workflows for automated posting, but they require manual triggering and confirmation.

## Security Notes

- Never commit `.env` files
- Never commit actual API credentials
- Use GitHub Secrets for CI/CD
- Always use read/write scoped tokens

## Development Workflow

1. Make changes in a test script
2. Show the user what the script will do
3. Let the USER run the script
4. Never execute posting code without permission

## AI-Specific Instructions

When asked to post something:
1. First, create a script
2. Explain what it will do
3. Ask for permission
4. Let the user run it

When testing:
1. Use print statements
2. Use dry-run modes
3. Never make actual API calls without permission

When asked to delete content:
1. **READ every post's full content first**
2. **CHECK the date** - never delete old content without explicit confirmation
3. **SHOW the user** exactly what will be deleted
4. **UNDERSTAND replies** are usually legitimate engagement
5. **GET explicit confirmation** before any deletion
6. **BE CONSERVATIVE** - preserve content when uncertain

## Remember

**The user's social media accounts are their own. Never post without explicit, clear permission for each specific post.**

**Every post represents real engagement with the PolicyEngine community. Treat all content with extreme care. When in doubt, preserve rather than delete. Historical content is valuable and irreplaceable.**