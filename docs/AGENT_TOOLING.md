jjj
# AI Agent Tooling

> Skills, commands, hooks, and the `agents` CLI for cross-agent configuration management.

## The `agents` CLI

The [agents CLI](https://github.com/ywatanabe1989/agents) (fork of [amtiYo/agents](https://github.com/amtiYo/agents)) provides one `.agents/` directory as a single source of truth, syncing MCP servers, skills, and instructions to every AI coding tool automatically.

It is pre-installed in SciTeX containers and auto-runs `agents sync --quiet` on every terminal login via `.bashrc`.

### Key Commands

| Command | Description |
|---------|-------------|
| `agents start` | Interactive setup: pick integrations, add MCP servers, sync |
| `agents sync` | Regenerate all tool configs from `.agents/agents.json` |
| `agents status` | Show integrations, MCP servers, file states, live probes |
| `agents doctor` | Validate configs and suggest fixes (`--fix` to auto-fix) |
| `agents mcp add <name>` | Add an MCP server interactively |
| `agents mcp list` | List all configured MCP servers |
| `agents mcp test` | Validate server definitions (`--runtime` for live checks) |
| `agents watch` | Auto-sync when `.agents/` files change |

### Config Files

```
<project>/
  .agents/
    agents.json     # Single source of truth (schema v3, committed)
    local.json      # Secrets & overrides (gitignored)
    skills/         # Reusable skill definitions (committed)
  AGENTS.md         # Unified instructions for all AI tools
```

On `agents sync`, the config is propagated to each tool's native format:
`.mcp.json` (Claude Code), `.codex/config.toml` (Codex), `.gemini/settings.json` (Gemini), etc.

## Skills

Skills are reusable knowledge files that AI agents load for domain-specific guidance. SciTeX provides **platform skills** (auto-generated) and supports **user/project skills** (custom).

### Platform Skills (Auto-Generated)

SciTeX compiles a `SKILL.md` from all registered app modules and deploys it to `~/.claude/skills/scitex-hub/SKILL.md` on every terminal connect. Built dynamically from `apps/*/skill.py` registrations.

| Module | MCP Prefixes | Capabilities |
|--------|-------------|--------------|
| Console | `project_*`, `introspect_*`, `template_*` | File management, terminal, code execution, Jupyter |
| Visualizer | `plt_*` | Create/edit plots, compose figures, export publication-ready |
| Scholar | `crossref_*`, `scholar_*`, `openalex_*` | Search papers, manage bibliography, citation graphs, PDFs |
| Writer | `writer_*` | LaTeX editing, compile to PDF, figures/tables/bibliography |
| Clew | `clew_*` | Pipeline DAGs, chain steps, run with status tracking |
| Workspace | — | Three-column layout, module switching |
| Hub | — | Project dashboard, activity feed, quick actions |
| Notebook | — | Experiment logger (DataStore, FileVault, JobQueue) |
| Apps | — | Browse, install, publish community apps |
| App Maker | — | Create, edit, preview custom workspace modules |
| Examples | — | Interactive demos (plotting, stats, IO, sessions) |
| Tools | — | Shared utilities, converters, validators |

### User/Project Skills

Users can create custom skills in `.agents/skills/`:

```bash
mkdir -p .agents/skills/my-skill
cat > .agents/skills/my-skill/SKILL.md <<'EOF'
---
name: my-skill
description: Custom domain knowledge for my project
---

# My Skill
Guidelines and patterns for this project...
EOF

agents sync
```

After sync, the skill appears in: `.claude/skills/`, `.cursor/skills/`, `.gemini/skills/`, `.windsurf/skills/`

## Commands (Slash Commands)

**Claude Code** supports custom slash commands defined as Markdown files in `.claude/commands/`. Each file becomes a `/<name>` command.

```markdown
# .claude/commands/review.md
Review the current file for:
- Security vulnerabilities
- Performance issues
- Code style consistency
Use the project's linting rules from .eslintrc
```

Usage: type `/review` in Claude Code to invoke.

| Variable | Replaced With |
|----------|--------------|
| `$ARGUMENTS` | Text typed after the command name |

**SciTeX note:** SciTeX does not auto-generate custom commands. Users can create their own in any project's `.claude/commands/` directory. This feature is currently **Claude Code-specific**.

## Hooks

**Claude Code** hooks are shell scripts that execute in response to lifecycle events. They are defined in `.claude/hooks/` or in `.claude/settings.json`.

### Hook Events

| Event | When It Fires |
|-------|--------------|
| `PreToolUse` | Before a tool call executes (can block or modify) |
| `PostToolUse` | After a tool call completes (for logging, linting) |
| `Notification` | When Claude Code sends a notification |
| `Stop` | When the agent stops or completes a turn |

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "command": "eslint --fix $FILE_PATH"
      }
    ]
  }
}
```

**SciTeX note:** SciTeX does not auto-generate hooks. Users can create their own for custom workflows. This feature is currently **Claude Code-specific**.

## Cross-Agent Support

| Feature | Claude Code | Codex | Gemini CLI | Cursor | Copilot |
|---------|:-:|:-:|:-:|:-:|:-:|
| MCP Servers | ✓ | ✓ | ✓ | ✓ | ✓ |
| Skills | ✓ | ✓ | ✓ | ✓ | — |
| Instructions (AGENTS.md) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Commands | ✓ | — | — | — | — |
| Hooks | ✓ | — | — | — | — |

✓ = synced via `agents sync`  — = not supported by this tool

### Source Code

| File | Purpose |
|------|---------|
| `apps/llm_app/skills/registry.py` | `Skill` dataclass, `register()`, `build_aggregated_context()` |
| `apps/llm_app/skills/export.py` | `export_claude_skill()` → SKILL.md, `export_chat_prompt()` → chat system prompt |
| `apps/*/skill.py` | Per-app skill registration (12 modules) |
| `apps/console_app/services/agents_config.py` | Builds `agents.json`, `AGENTS.md`, `.mcp.json`, `SKILL.md` |
| `apps/console_app/views/terminal/dotfiles.py` | bashrc template with `agents sync` auto-run |
