# PolicyEngine Social Media Automation

Automated social media posting for PolicyEngine blog articles and announcements.

## Features

- 🤖 Auto-generates social posts from blog articles
- 🐦 Posts to X (Twitter) with thread support
- 💼 Posts to LinkedIn with professional formatting
- 📊 Tracks engagement and analytics
- ✅ Review process via GitHub PRs
- 📅 Scheduling and timezone optimization

## Setup

1. Clone this repository
2. Set up GitHub Secrets (see below)
3. Posts are automatically created when blog posts are merged

## How it Works

1. When a new blog post is published to `policyengine-app`, a GitHub Action triggers
2. The action creates a draft social media post as a PR in this repo
3. Team reviews and edits the content
4. Upon merge, posts are automatically published to X and LinkedIn
5. Analytics are tracked and reported back as GitHub issues

## Repository Structure

```
src/
└── policyengine_social/   # Main package
    ├── extract.py         # Image extraction
    ├── generate.py        # Post generation
    └── publish.py         # Publishing logic

tests/                     # Comprehensive test suite
├── test_extract_blog_images.py
├── test_generate_social_post.py
└── test_publish_to_x.py

posts/
├── queue/                 # Posts waiting to be published
├── published/             # Archive of published posts
└── drafts/                # Work in progress

.github/
└── workflows/             # GitHub Actions
```

## Installation

```bash
# Install the package
pip install -e ".[dev]"

# Install playwright for screenshots
playwright install chromium
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=policyengine_social

# Run specific test
pytest tests/test_extract_blog_images.py -v
```

## Required Secrets

Set these in your repository settings:

- `X_API_KEY` - X/Twitter API credentials
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_SECRET`
- `LINKEDIN_ACCESS_TOKEN` - LinkedIn API token
- `GITHUB_TOKEN` - For cross-repo access (auto-provided)

## Post Format

Posts are stored as YAML files with platform-specific content:

```yaml
title: "Post Title"
source: "blog/article-slug"
publish_at: "2024-08-19T10:00:00-05:00"  # Optional scheduling
platforms:
  x:
    thread:
      - "First tweet with engaging hook"
      - "Second tweet with details"
    media: ["image1.png"]
  linkedin:
    text: "Professional summary..."
    media: ["image1.png"]
```

## Usage

### Manual Trigger

To manually create a social post for a blog article:

1. Go to Actions tab
2. Select "Create Social Post from Blog"
3. Enter the blog slug
4. Review and merge the generated PR

### Automatic Trigger

Posts are automatically created when:
- A new blog post is merged to `policyengine-app`
- The post includes social media metadata

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.