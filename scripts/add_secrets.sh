#!/bin/bash
# Script to help add GitHub secrets for PolicyEngine social accounts
# Run this with your actual credentials

echo "Adding GitHub secrets for policyengine-social..."
echo "You'll need to have the GitHub CLI (gh) installed and authenticated"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed. Install it with: brew install gh"
    exit 1
fi

# Navigate to repo
cd /Users/maxghenis/PolicyEngine/policyengine-social

echo "📝 Instructions:"
echo "1. Copy your API credentials from your .env file"
echo "2. Run the commands below one at a time"
echo "3. Paste the value when prompted (it will be hidden)"
echo ""
echo "Run these commands:"
echo ""

# Commands for @thepolicyengine
echo "# For @thepolicyengine account:"
echo "gh secret set X_THEPOLICYENGINE_API_KEY"
echo "gh secret set X_THEPOLICYENGINE_API_SECRET"
echo "gh secret set X_THEPOLICYENGINE_ACCESS_TOKEN"
echo "gh secret set X_THEPOLICYENGINE_ACCESS_TOKEN_SECRET"
echo ""

# Commands for @policyengineus
echo "# For @policyengineus account:"
echo "gh secret set X_POLICYENGINEUS_API_KEY"
echo "gh secret set X_POLICYENGINEUS_API_SECRET"
echo "gh secret set X_POLICYENGINEUS_ACCESS_TOKEN"
echo "gh secret set X_POLICYENGINEUS_ACCESS_TOKEN_SECRET"
echo ""

# Commands for @policyengineuk
echo "# For @policyengineuk account (when you have them):"
echo "gh secret set X_POLICYENGINEUK_API_KEY"
echo "gh secret set X_POLICYENGINEUK_API_SECRET"
echo "gh secret set X_POLICYENGINEUK_ACCESS_TOKEN"
echo "gh secret set X_POLICYENGINEUK_ACCESS_TOKEN_SECRET"
echo ""

# Zapier webhook (optional)
echo "# For LinkedIn via Zapier (optional):"
echo "gh secret set ZAPIER_LINKEDIN_WEBHOOK"
echo ""

echo "📌 To verify secrets were added:"
echo "gh secret list"