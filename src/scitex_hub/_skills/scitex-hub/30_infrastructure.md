---
description: |
  [TOPIC] Infrastructure CLI
  [DETAILS] Infrastructure management — environment setup, Docker container management, deploy, logs, SSH, and MCP server start/diagnose..
tags: [scitex-hub-infrastructure]
---

# Infrastructure CLI

## Setup

```bash
scitex-hub setup [--env dev|prod] [--force]
```

Interactive wizard: checks prerequisites (docker, git), creates `.env` from template, validates docker-compose file.

```bash
scitex-hub setup              # interactive, prompts for env
scitex-hub setup --env dev    # dev environment
scitex-hub setup --env prod   # production environment
scitex-hub setup --env dev --force   # overwrite existing .env
```

## Docker

```bash
scitex-hub docker [--env dev|prod] build [--no-cache]
scitex-hub docker [--env dev|prod] up    [-d]           # start (detached default)
scitex-hub docker [--env dev|prod] down  [-v]           # stop (--volumes to remove)
scitex-hub docker [--env dev|prod] restart
scitex-hub docker [--env dev|prod] ps                   # show container status
```

## Deploy and Status

```bash
scitex-hub deploy                   # deploy with current settings
scitex-hub status                   # show deployment health
scitex-hub logs [service]           # tail service logs
scitex-hub ssh                      # SSH into cloud
```

## MCP Server

```bash
# Start
scitex-hub mcp start                          # stdio (Claude Desktop default)
scitex-hub mcp start -t sse                   # SSE (deprecated, avoid)
scitex-hub mcp start -t http                  # HTTP streamable (recommended for remote)
scitex-hub mcp start -t http --host 0.0.0.0 --port 8086

# Diagnose
scitex-hub mcp doctor                         # check deps, tea CLI, API key
scitex-hub mcp installation                   # show client config snippets
scitex-hub mcp list-tools [-v] [-vv] [--json] # list all MCP tools
```

### MCP Client Configuration

Local (stdio, Claude Desktop):
```json
{
  "mcpServers": {
    "scitex-hub": {
      "command": "scitex-hub",
      "args": ["mcp", "start"],
      "env": {
        "SCITEX_HUB_API_KEY": "your-api-key"
      }
    }
  }
}
```

Remote (HTTP):
```json
{
  "mcpServers": {
    "scitex-hub-remote": {
      "url": "http://your-server:8086/mcp"
    }
  }
}
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SCITEX_HUB_API_KEY` | API key for cloud operations |
| `SCITEX_HUB_URL` | Cloud server URL (default: `https://scitex.cloud`) |
| `SCITEX_HUB_MCP_HOST` | MCP server bind host |
| `SCITEX_HUB_MCP_PORT` | MCP server port (default: 8086) |

## DockerManager (Python API)

```python
from scitex_hub import DockerManager, get_environment

env = get_environment("dev")        # or "prod"
docker = DockerManager(env)

docker.build(no_cache=False)
docker.up(detach=True)
docker.down(volumes=False)
docker.restart()
docker.ps()
```

## MCP Onsite Tools (AI agent browser control)

| Tool | What it does |
|------|-------------|
| `cloud_onsite_capture_page` | Screenshot current page |
| `cloud_onsite_eval_js` | Execute JavaScript in browser |
| `cloud_onsite_ui_action` | Drive UI actions (click, fill, navigate, scroll) |
| `cloud_onsite_get_context` | Get page context for AI agents |
| `cloud_onsite_check_permission` | Check API permissions |
| `cloud_onsite_get_dev_app_url` | Get dev server URL for app |
| `cloud_api_status` | Check cloud API status |

# EOF
