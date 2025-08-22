# PolicyEngine Social Media Setup Guide

## X (Twitter) Account Setup

### 1. Get API Credentials for Each Account

For each account (@thepolicyengine, @policyengineus, @policyengineuk):

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create an app or select existing one
3. Go to "Keys and tokens"
4. Generate/regenerate:
   - API Key and Secret (Consumer Keys)
   - Access Token and Secret (with "Read and Write" permissions)

### 2. Local Configuration

Copy the example config and add your credentials:

```bash
cp config/x_accounts.example.yaml config/x_accounts.yaml
# Edit with your actual credentials
```

### 3. GitHub Actions Setup

Add these secrets to your GitHub repository:
(Settings → Secrets and variables → Actions → New repository secret)

For @thepolicyengine:
- `X_POLICYENGINE_API_KEY`
- `X_POLICYENGINE_API_SECRET`
- `X_POLICYENGINE_ACCESS_TOKEN`
- `X_POLICYENGINE_ACCESS_TOKEN_SECRET`

For @policyengineus:
- `X_POLICYENGINEUS_API_KEY`
- `X_POLICYENGINEUS_API_SECRET`
- `X_POLICYENGINEUS_ACCESS_TOKEN`
- `X_POLICYENGINEUS_ACCESS_TOKEN_SECRET`

For @policyengineuk:
- `X_POLICYENGINEUK_API_KEY`
- `X_POLICYENGINEUK_API_SECRET`
- `X_POLICYENGINEUK_ACCESS_TOKEN`
- `X_POLICYENGINEUK_ACCESS_TOKEN_SECRET`

## LinkedIn Setup (via Zapier)

1. Create a Zapier account at https://zapier.com
2. Create a new Zap:
   - Trigger: Webhooks by Zapier → Catch Hook
   - Action: LinkedIn → Share Update
3. Copy the webhook URL
4. Add to GitHub secrets:
   - `ZAPIER_LINKEDIN_WEBHOOK`
   - `ZAPIER_ALL_WEBHOOK` (if using multi-platform Zap)

## Usage Examples

### From Command Line

```bash
# Install the package
pip install -e .

# Post to specific account
pe-social post-x "Hello from PolicyEngine!" --account policyengineus

# Post to all accounts
pe-social batch "New feature announcement!"

# Generate and post from blog
pe-social generate --url https://policyengine.org/us/research/some-post
pe-social post-x --thread generated_posts.txt --account thepolicyengine

# Post with images
pe-social post-x "Check out our latest analysis!" --images chart1.png chart2.png
```

### From GitHub Actions

1. Go to Actions tab in GitHub
2. Select "Post to Social Media" workflow
3. Click "Run workflow"
4. Fill in:
   - Blog URL or custom message
   - Platform (X, LinkedIn, or all)
   - Account (for X posts)
5. Click "Run workflow"

### From Python

```python
from policyengine_social.publishers.x_multi import MultiAccountXPublisher

# Initialize publisher
publisher = MultiAccountXPublisher("config/x_accounts.yaml")

# Post to specific account
result = publisher.post(
    text="Hello from Python!",
    account="policyengineus"
)

# Post thread
result = publisher.post_thread(
    posts=["First tweet", "Second tweet", "Third tweet"],
    account="thepolicyengine"
)

# Smart routing based on content
account = publisher.route_by_content(
    text="New UK tax analysis shows...",
    tags=["uk", "tax"]
)  # Returns: "policyengineuk"
```

## Content Routing

The system automatically routes content to the appropriate account based on:

1. **Tags**: `us` → @policyengineus, `uk` → @policyengineuk
2. **Categories**: `us-analysis` → @policyengineus, etc.
3. **Content detection**: Mentions of "United States" → @policyengineus
4. **Default**: @thepolicyengine for general content

## Testing

Before posting to production accounts:

1. Create test apps in X Developer Portal
2. Use test account credentials
3. Test with `--dry-run` flag (if implemented)
4. Verify in GitHub Actions with manual trigger

## Troubleshooting

### 403 Forbidden Error
- Regenerate Access Token after enabling "Read and Write" permissions
- Make sure you saved the app settings before regenerating

### Rate Limits
- X allows 300 posts per 3 hours per app
- Add delays between posts in threads
- Use different apps for different accounts if needed

### GitHub Actions Fails
- Check that all secrets are set correctly
- Verify credentials work locally first
- Check Actions logs for specific error messages