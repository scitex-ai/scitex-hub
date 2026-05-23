---
description: |
  [TOPIC] Gitea CLI
  [DETAILS] Gitea Git hosting CLI — repository management, fork, clone, PR, issue, push/pull, auth. Backend is git.scitex.ai via the `tea` CLI wrapper..
tags: [scitex-hub-gitea-cli]
---

# Gitea CLI

All commands under `scitex-hub gitea`. Backend: `git.scitex.ai` (wraps the `tea` CLI).

## Authentication

```bash
scitex-hub gitea login    # authenticate with Gitea
scitex-hub gitea logout   # clear credentials
```

## Repository Management

```bash
scitex-hub gitea create <name>           # create repo on Gitea
scitex-hub gitea list                    # list your repos
scitex-hub gitea search <query>          # search repos
scitex-hub gitea clone <user/repo>       # clone from Gitea
scitex-hub gitea fork <user/repo>        # fork a repo
scitex-hub gitea delete <user/repo>      # delete a repo
scitex-hub gitea status                  # show current repo status
```

## Collaboration

```bash
# Pull requests
scitex-hub gitea pr create               # open a PR
scitex-hub gitea pr list                 # list open PRs

# Issues
scitex-hub gitea issue create            # create an issue
scitex-hub gitea issue list              # list issues

# Sync committed changes
scitex-hub gitea push [remote] [branch]  # push to Gitea
scitex-hub gitea pull [remote] [branch]  # pull from Gitea
```

## MCP Tools

| Tool | What it does |
|------|-------------|
| `cloud_repo_login` | Authenticate with Gitea |
| `cloud_repo_create` | Create repository |
| `cloud_repo_list` | List repositories |
| `cloud_repo_search` | Search repositories |
| `cloud_repo_clone` | Clone repository |
| `cloud_repo_fork` | Fork repository |
| `cloud_repo_delete` | Delete repository |
| `cloud_repo_status` | Repository status |
| `cloud_repo_push` | Push commits to Gitea |
| `cloud_repo_pull` | Pull commits from Gitea |
| `cloud_repo_pr_create` | Create pull request |
| `cloud_repo_pr_list` | List pull requests |
| `cloud_repo_issue_create` | Create issue |
| `cloud_repo_issue_list` | List issues |

## Notes

- `push`/`pull` here are git-level operations on committed changes.
  For uncommitted working file sync, see [sync-architecture.md](sync-architecture.md).
- `tea` binary must be installed: `~/.local/bin/tea`
  Install: `wget https://dl.gitea.com/tea/0.9.2/tea-0.9.2-linux-amd64 -O ~/.local/bin/tea && chmod +x ~/.local/bin/tea`

## Examples

```bash
scitex-hub gitea login
scitex-hub gitea create my-new-repo
scitex-hub gitea clone ywatanabe/my-new-repo
cd my-new-repo
# ... make changes, git commit ...
scitex-hub gitea push
scitex-hub gitea pr create
```

# EOF
