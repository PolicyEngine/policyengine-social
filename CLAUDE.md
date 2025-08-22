# PolicyEngine Social Media Automation - AI Development Guidelines

## CRITICAL RULES - NEVER VIOLATE THESE

### 🚨 NEVER POST WITHOUT EXPLICIT PERMISSION
- **NEVER run any code that posts to social media without explicit user permission**
- **NEVER test posting functionality with actual posts**
- **ALWAYS use dry-run mode or print statements for testing**
- **ALWAYS ask "May I post this?" before executing any posting code**
- If testing is needed, create scripts for the USER to run, don't run them yourself

### Example of what NOT to do:
```python
# ❌ NEVER DO THIS WITHOUT PERMISSION
publisher.post("Test message")  # DO NOT RUN
```

### Example of safe testing:
```python
# ✅ Safe - just prints what would be posted
print(f"Would post: {message}")
print(f"To account: @{account}")
# Don't actually call publisher.post()
```

## Repository Overview

This repository handles automated social media posting for PolicyEngine across multiple platforms:
- X (Twitter): @thepolicyengine, @policyengineus, @policyengineuk
- LinkedIn: Via Zapier webhooks

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

## Remember

**The user's social media accounts are their own. Never post without explicit, clear permission for each specific post.**