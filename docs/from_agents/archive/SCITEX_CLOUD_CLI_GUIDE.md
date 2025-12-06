# SciTeX Cloud CLI - Complete Guide

**Version:** 2.0.0
**Updated:** 2025-10-20
**Status:** Production Ready ✅

---

## Overview

The `scitex cloud` command provides Git hosting operations through Gitea, similar to `gh` (GitHub CLI) and `tea` (Gitea CLI), but integrated into the unified SciTeX platform.

---

## Installation

```bash
# Install scitex package
pip install scitex

# Verify installation
scitex --version
scitex cloud --help
```

---

## Quick Start

### 1. Login to SciTeX Cloud

```bash
# Interactive login (prompts for token)
scitex cloud login

# Login with token directly
scitex cloud login --url http://localhost:3001 --token YOUR_TOKEN

# For production (when available)
scitex cloud login --url https://git.scitex.ai --token YOUR_TOKEN
```

**Where to get your token:**
1. Go to your Gitea instance (e.g., http://localhost:3001)
2. Settings → Applications → Generate New Token
3. Copy the token and use it in login command

### 2. List Your Repositories

```bash
# List all your repositories
scitex cloud list

# List repositories for specific user
scitex cloud list --user ywatanabe

# List starred repositories
scitex cloud list --starred

# List watched repositories
scitex cloud list --watched
```

### 3. Clone a Repository

```bash
# Clone with short name (auto-detects owner)
scitex cloud clone django-gitea-demo

# Clone with full path
scitex cloud clone ywatanabe/my-research

# Clone to specific directory
scitex cloud clone ywatanabe/my-research ./my-local-dir
```

---

## All Commands

### Repository Management

#### Create Repository

```bash
# Create public repository
scitex cloud create my-new-project

# Create private repository with description
scitex cloud create my-research \
  --description "My neuroscience research project" \
  --private
```

**Options:**
- `--description`, `-d`: Repository description
- `--private`: Make repository private (default: public)
- `--login`, `-l`: Specify tea login to use (default: scitex-dev)

#### List Repositories

```bash
# List all your repositories
scitex cloud list

# List for specific user
scitex cloud list --user ywatanabe

# List starred repos
scitex cloud list --starred

# List watched repos
scitex cloud list --watched
```

**Options:**
- `--user`, `-u`: List repos for specific user
- `--starred`, `-s`: List starred repositories
- `--watched`, `-w`: List watched repositories
- `--login`, `-l`: Specify tea login to use

#### Search Repositories

```bash
# Search for repositories
scitex cloud search neural

# Search with quoted query
scitex cloud search "machine learning"

# Limit results
scitex cloud search neuroscience --limit 20
```

**Options:**
- `--limit`: Maximum number of results (default: 10)
- `--login`, `-l`: Specify tea login to use

#### Delete Repository

```bash
# Delete repository (with confirmation)
scitex cloud delete ywatanabe/test-repo
```

**⚠️ WARNING:**
- This action cannot be undone!
- Requires confirmation
- Must use full `username/repo` format

**Options:**
- `--login`, `-l`: Specify tea login to use

---

### Cloning and Forking

#### Clone Repository

```bash
# Clone with auto-detection
scitex cloud clone repo-name

# Clone with full path
scitex cloud clone user/repo-name

# Clone to specific directory
scitex cloud clone user/repo ./local-dir
```

**Features:**
- ✅ Auto-detects owner if only repo name provided
- ✅ Uses configured SSH/HTTP settings
- ✅ Supports custom destination directory

#### Fork Repository

```bash
# Fork a repository
scitex cloud fork lab-pi/shared-project
```

---

### Git Operations

#### Push Changes

```bash
# Push current branch to origin
scitex cloud push
```

Equivalent to: `git push origin <current-branch>`

#### Pull Changes

```bash
# Pull latest changes
scitex cloud pull
```

Equivalent to: `git pull origin <current-branch>`

#### Show Status

```bash
# Show repository status
scitex cloud status
```

Equivalent to: `git status`

---

### Pull Requests

#### Create Pull Request

```bash
# Create PR interactively
scitex cloud pr create

# Create PR with details
scitex cloud pr create \
  --title "Add analysis pipeline" \
  --description "Implements new neural network analysis" \
  --base main \
  --head feature-branch
```

**Options:**
- `--title`, `-t`: PR title
- `--description`, `-d`: PR description
- `--base`, `-b`: Base branch (default: main)
- `--head`, `-h`: Head branch

#### List Pull Requests

```bash
# List all pull requests
scitex cloud pr list
```

---

### Issues

#### Create Issue

```bash
# Create issue
scitex cloud issue create \
  --title "Bug in preprocessing" \
  --body "Detailed description of the bug"
```

**Options:**
- `--title`, `-t`: Issue title (required)
- `--body`, `-b`: Issue body/description

#### List Issues

```bash
# List all issues
scitex cloud issue list
```

---

## Configuration

### Tea Configuration File

Location: `~/.config/tea/config.yml`

```yaml
logins:
- name: scitex-dev              # Login name
  url: http://localhost:3001    # Gitea instance URL
  token: YOUR_TOKEN_HERE        # API token
  user: your-username           # Your username
  ssh_host: localhost           # SSH host
  default: false                # Default login
```

### Environment Variables

```bash
# Optional: Set default login
export SCITEX_CLOUD_LOGIN=scitex-dev

# Optional: Set Gitea URL
export SCITEX_CLOUD_URL=http://localhost:3001
```

---

## Common Workflows

### Workflow 1: Start New Research Project

```bash
# Create repository
scitex cloud create neuroscience-study \
  --description "Spike sorting research" \
  --private

# Clone it locally
scitex cloud clone neuroscience-study

# Work on your project
cd neuroscience-study/
echo "# Neuroscience Study" > README.md
git add README.md
git commit -m "Initial commit"

# Push changes
scitex cloud push
```

### Workflow 2: Collaborate on Existing Project

```bash
# Fork the project
scitex cloud fork lab-pi/shared-analysis

# Clone your fork
scitex cloud clone shared-analysis

# Create feature branch
cd shared-analysis/
git checkout -b my-contribution

# Make changes and commit
git add .
git commit -m "Add new analysis method"

# Push to your fork
scitex cloud push

# Create pull request
scitex cloud pr create \
  --title "Add new analysis method" \
  --description "Implements improved spike detection algorithm"
```

### Workflow 3: Search and Clone

```bash
# Search for relevant repositories
scitex cloud search "neural networks"

# Clone interesting one
scitex cloud clone researcher/neural-net-analysis

# Start working
cd neural-net-analysis/
```

### Workflow 4: Clean Up Old Projects

```bash
# List all repositories
scitex cloud list

# Delete test repositories
scitex cloud delete ywatanabe/old-test-1
scitex cloud delete ywatanabe/old-test-2
```

---

## Comparison with Other CLIs

### vs `gh` (GitHub CLI)

| Feature | scitex cloud | gh |
|---------|--------------|-----|
| Repository management | ✅ | ✅ |
| Pull requests | ✅ | ✅ |
| Issues | ✅ | ✅ |
| Scientific workflows | ✅ | ❌ |
| Works with Gitea | ✅ | ❌ |
| Works with GitHub | ❌ | ✅ |

### vs `tea` (Gitea CLI)

| Feature | scitex cloud | tea |
|---------|--------------|-----|
| Gitea operations | ✅ | ✅ |
| Repository search | ✅ | ✅ |
| Repository delete | ✅ | ❌ |
| Auto-owner detection | ✅ | ❌ |
| Integrated with Scholar/Code/Viz | ✅ | ❌ |

---

## Troubleshooting

### Command Not Found

```bash
# Check if scitex is installed
pip list | grep scitex

# Reinstall if needed
pip install --upgrade scitex
```

### Authentication Errors

```bash
# Check login configuration
cat ~/.config/tea/config.yml

# Re-login
scitex cloud login --url YOUR_URL --token YOUR_TOKEN
```

### Clone Fails

```bash
# Try with full path
scitex cloud clone username/repo-name

# Check repository exists
scitex cloud list --user username
```

### Delete Requires PyYAML

```bash
# Install PyYAML if missing
pip install pyyaml
```

---

## Advanced Usage

### Using Multiple Logins

```bash
# Login to development instance
scitex cloud login --url http://localhost:3001 --token DEV_TOKEN
# This creates login 'scitex' by default

# Login to production
tea login add --name scitex-prod --url https://git.scitex.ai --token PROD_TOKEN

# Use specific login
scitex cloud list --login scitex-prod
scitex cloud clone my-repo --login scitex-prod
```

### Batch Operations

```bash
# Clone multiple repositories
for repo in repo1 repo2 repo3; do
  scitex cloud clone "ywatanabe/$repo"
done

# Delete multiple test repositories
for i in {1..5}; do
  scitex cloud delete "ywatanabe/test-$i"
done
```

---

## API Reference

All commands are implemented using:
1. **tea CLI** - For standard Git operations
2. **Gitea REST API** - For operations not supported by tea (e.g., delete)

### Dependencies

- `click` - CLI framework
- `requests` - HTTP client (for API calls)
- `pyyaml` - YAML parser (for config reading)
- `tea` - Gitea CLI tool

---

## Future Enhancements

### Planned Features

- [ ] `scitex cloud star <repo>` - Star repositories
- [ ] `scitex cloud watch <repo>` - Watch repositories
- [ ] `scitex cloud archive <repo>` - Archive repositories
- [ ] `scitex cloud rename <old> <new>` - Rename repositories
- [ ] `scitex cloud transfer <repo> <new-owner>` - Transfer ownership
- [ ] Bash/Zsh completion support
- [ ] Repository templates support
- [ ] Webhooks management
- [ ] Organization management

---

## Getting Help

```bash
# General help
scitex --help

# Cloud commands help
scitex cloud --help

# Specific command help
scitex cloud clone --help
scitex cloud create --help
scitex cloud delete --help
```

---

## Related Documentation

- [SciTeX Cloud Command Strategy](/home/ywatanabe/proj/scitex-cloud/TODOS/10_SCITEX_CLOUD_COMMAND.md)
- [CLI Fix Session Summary](/home/ywatanabe/proj/scitex-cloud/docs/SESSION_SUMMARY_2025-10-20_SCITEX_CLI_FIX.md)
- [Gitea Integration](/home/ywatanabe/proj/scitex-cloud/docs/DJANGO_GITEA_ARCHITECTURE.md)

---

**Last Updated:** 2025-10-20
**Maintainer:** SciTeX Team
**License:** MIT

<!-- EOF -->
