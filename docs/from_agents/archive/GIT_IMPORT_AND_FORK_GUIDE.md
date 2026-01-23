# Git Import and Fork Guide

## Overview
SciTeX Cloud supports importing (forking) repositories from various Git hosting services including GitHub, GitLab, Bitbucket, and other Git servers.

## Supported Import Methods

### 1. Direct Git Clone (Recommended for most users)
The simplest method that works with any Git repository.

**When to use:**
- Importing public repositories
- Quick import without full migration features
- Works with any Git-compatible service

**How it works:**
1. Go to "New Repository"
2. Select "Import from GitHub/GitLab"
3. Enter the repository URL (HTTPS or SSH)
4. The repository name will be auto-filled from the URL
5. Click "Create" to clone the repository

**URL Formats Supported:**
```
# HTTPS
https://github.com/username/repo.git
https://gitlab.com/username/repo.git
https://bitbucket.org/username/repo.git

# SSH (requires SSH key setup)
git@github.com:username/repo.git
git@gitlab.com:username/repo.git
```

### 2. Gitea Migration API (Advanced)
Uses Gitea's migration API for full repository import including issues, PRs, etc.

**When to use:**
- Need to preserve issues, pull requests, wiki
- Migrating from GitHub/GitLab with full history
- Creating a mirror that stays in sync

**Features:**
- Import issues, pull requests, releases
- Import wiki pages
- Import labels and milestones
- Optional: Create as mirror (stays synced)

**Supported Services:**
- GitHub
- GitLab
- Gitea
- Gogs

## Repository Name Preservation

When importing, SciTeX Cloud now automatically extracts and uses the original repository name from the URL:

**Examples:**
```
https://github.com/user/my-project.git → Project name: "my-project"
git@gitlab.com:org/awesome-tool.git → Project name: "awesome-tool"
```

You can override this by providing a custom name in the "Repository Name" field.

## Private Repository Access

### For HTTPS URLs:
1. Generate a personal access token from your Git service:
   - GitHub: Settings → Developer Settings → Personal Access Tokens
   - GitLab: Preferences → Access Tokens
   - Bitbucket: Settings → App Passwords

2. Either:
   - Enter token during import (one-time use)
   - Save token in profile settings (reusable)

### For SSH URLs:
1. Generate an SSH key in Profile Settings → SSH Keys
2. Add the public key to your Git service
3. Use SSH format URLs for cloning

## Gitea Integration

SciTeX Cloud includes an integrated Gitea instance that:
- Provides local Git hosting
- Enables version control for all projects
- Supports Git operations (push, pull, branches, etc.)

**Configuration:**
- URL: http://localhost:3000 (default)
- API available at: http://localhost:3000/api/v1
- Token configured via environment variables

## API Reference

The Gitea API client (`apps/gitea_app/api_client.py`) provides these methods:

### `migrate_repository()`
```python
client.migrate_repository(
    clone_addr="https://github.com/user/repo.git",
    repo_name="my-repo",  # Optional, extracted from URL if not provided
    service="github",     # github, gitlab, gitea, gogs
    auth_token="xxx",     # Optional, for private repos
    mirror=False,         # True to keep synced
    issues=True,          # Import issues
    pull_requests=True,   # Import PRs
    wiki=True,           # Import wiki
    releases=True        # Import releases
)
```

### `fork_repository()`
```python
client.fork_repository(
    owner="username",
    repo="repository-name",
    organization="my-org"  # Optional, for org forks
)
```

## Troubleshooting

### Issue: Repository name changed during import
**Solution:** The auto-extraction feature now preserves the original name. If you want a custom name, enter it manually in the "Repository Name" field.

### Issue: Private repository access denied
**Solution:**
1. Ensure you've provided a valid access token
2. Token must have `repo` scope (GitHub) or equivalent permissions
3. For SSH, verify your public key is added to the Git service

### Issue: Clone fails with authentication error
**Solution:**
- For HTTPS: Use personal access token
- For SSH: Set up SSH key in profile settings
- Verify repository is accessible with provided credentials

## Best Practices

1. **Use SSH for frequent operations**: Set up SSH keys once, use for all repositories
2. **Save tokens in profile**: Avoid entering tokens repeatedly
3. **Preserve original names**: Let the auto-extraction use the original repository name
4. **Use Gitea for local development**: Take advantage of integrated Git hosting
5. **Mirror important repositories**: Use mirror option for critical dependencies

## Future Enhancements

Planned features:
- Automatic fork detection
- Repository synchronization UI
- Bulk import tool
- GitHub/GitLab webhooks integration
- Automated backup to external services
