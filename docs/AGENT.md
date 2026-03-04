# Agent Integration

> AI coding agents (Claude, Codex, Gemini) work inside SciTeX terminals with shared MCP tools.

## Supported Agents

| Agent | Package | Command |
|-------|---------|---------|
| Claude Code | `@anthropic-ai/claude-code` | `claude` |
| OpenAI Codex | `@openai/codex` | `codex` |
| Google Gemini | `@google/gemini-cli` | `gemini` |

All three are installed automatically on first terminal login via nvm + npm
(see [HOME Directory > .bashrc](#bashrc)).

## Agent Sources

Agents are installed as global npm packages inside the Apptainer container:

```
~/.nvm/           # Node Version Manager (v0.40.1)
~/.npm-global/    # npm global prefix
  bin/
    claude        # @anthropic-ai/claude-code
    codex         # @openai/codex
    gemini        # @google/gemini-cli
    agents        # @agents-dev/cli (config synchronizer)
```

Installation is one-time per user. The `.ai-cli-installed` sentinel file
prevents re-running on subsequent logins.

## Agent Configs

### The `agents` Package

The [`@agents-dev/cli`](https://github.com/amtiYo/agents) package synchronizes
MCP server configuration across all AI coding tools from a single source of truth:

```
<project>/
  .agents/
    agents.json    # Single source of truth (schema v3)
    local.json     # Secrets (gitignored)
  AGENTS.md        # Project description for AI tools
  CLAUDE.md        # Claude Code-specific instructions
  .mcp.json        # Claude Code MCP server (direct fallback)
```

### agents.json

Auto-generated on terminal connect (`ensure_agents_config()`):

```json
{
  "schemaVersion": 3,
  "instructions": {"path": "AGENTS.md"},
  "integrations": {
    "enabled": ["claude", "codex", "gemini", "cursor", "copilot_vscode"]
  },
  "mcp": {
    "servers": {
      "scitex": {
        "label": "SciTeX Platform",
        "description": "145+ MCP tools for plotting, statistics, literature, writing",
        "transport": "stdio",
        "command": "/usr/local/bin/scitex",
        "args": ["mcp", "start"],
        "env": {
          "SCITEX_MCP_USE_PLT": "1",
          "SCITEX_MCP_USE_STATS": "1",
          "SCITEX_MCP_USE_SCHOLAR": "1",
          "..."
        }
      }
    }
  }
}
```

### Synchronization

On every login, `.bashrc` runs:

```bash
if command -v agents &>/dev/null && [ -d ".agents" ]; then
    agents sync --quiet 2>/dev/null
fi
```

This propagates `agents.json` to each tool's native config format:
- Claude Code: `.mcp.json`
- Codex: its own config
- Gemini: its own config

### MCP Tool Groups

All groups are enabled by default:

| Group | Tools |
|-------|-------|
| PLT | Plotting (line, scatter, bar, heatmap, ...) |
| STATS | Statistical tests (t-test, ANOVA, ...) |
| SCHOLAR | Literature search, PDF download, BibTeX |
| WRITER | LaTeX manuscript compilation |
| CLEW | Workflow pipeline management |
| AUDIO | Text-to-speech |
| DIAGRAM | Mermaid, Graphviz diagrams |
| CAPTURE | Screenshots |
| INTROSPECT | API inspection (signature, source, docstring) |
| TEMPLATE | Project templates |
| PROJECT | File I/O within project |
| DATASET | OpenNeuro, DANDI, PhysioNet |
| DEV | Development tools (versions, testing) |
| LINTER | Code quality checks |
| SOCIAL | Social media posting |
| UI | Browser notifications |
| USAGE | Usage tracking |

### Source Code

| File | Purpose |
|------|---------|
| `apps/console_app/services/agents_config.py` | Config generation + `ensure_agents_config()` |
| `apps/console_app/views/terminal/dotfiles.py` | bashrc template with auto-install + sync |
| `apps/console_app/views/terminal/workspace.py` | Workspace setup calling agents config |
