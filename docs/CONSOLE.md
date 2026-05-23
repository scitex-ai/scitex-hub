# Console

> Browser-based terminal running inside Apptainer containers via SLURM.

## Life Cycle

### Session States

```
SPAWNING → RUNNING → EXITED → RESPAWNING → RUNNING
                                    ↓ (max 5 retries)
                                   DEAD
```

| State | Description |
|-------|-------------|
| `SPAWNING` | PTY fork in progress |
| `RUNNING` | Shell active, reader thread streaming output |
| `EXITED` | Shell process ended, cleanup pending |
| `RESPAWNING` | Auto-restart after exit (with backoff) |
| `DEAD` | Terminal closed or max respawns exceeded |

### Connection Flow

```
Browser WebSocket (?project_id=N)
    → TerminalConsumer.connect()
    → Resolve project from selector  # Active project or dotfiles (id=0)
    → ensure_workspace()             # Create dirs, dotfiles, agent configs
    → Terminal Broker (IPC)          # Isolated process, no asyncio
    → pty.fork()                     # Inside broker process
    → srun --pty bash                # SLURM allocates resources
    → apptainer exec --pwd ~/proj/<slug> # Containerized shell in project dir
    → MOTD injection                 # Welcome message (0.8s delay)
```

### Terminal Broker

All PTY operations run in a separate broker process to prevent Daphne asyncio
deadlocks. Communication uses length-prefixed JSON over a Unix socket
(`/tmp/scitex-terminal-broker.sock`).

See `docs/TERMINAL_BROKER_ARCHITECTURE.md` for details.

### Respawn

When a shell exits, the broker auto-respawns up to 5 times.
The respawn counter resets after 10 seconds of stable runtime.
If all 5 attempts fail quickly, the session transitions to `DEAD`.

### Project Context

The terminal opens in the **selected project's directory**. The project ID
flows from the header project selector through the WebSocket to Apptainer:

```
Header selector (data-active-project-id)
    → WebSocket URL (?project_id=N)
    → TerminalConsumer resolves Project model
    → project.slug → "~/proj/<slug>/"
    → apptainer exec --pwd /home/<user>/proj/<slug>
```

Falls back to `project_id=0` (dotfiles project) when no project is selected.

### Message of the Day

After shell initialization, the broker injects a welcome message directly
to the client (bypassing the shell to avoid prompt corruption). Controlled
by the `SCITEX_HUB_SHOW_MOTD` environment variable (default: `true`).

## Security

### SLURM-Only Execution

All terminals **require** SLURM. No direct Apptainer or plain bash fallbacks.
If SLURM is unavailable, the terminal is disabled with an error message.

### Resource Limits

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| CPU | 2 cores | `--cpus-per-task=2` |
| Memory | 4 GB | `--mem=4G` |
| Time | 4 hours | `--time=04:00:00` |
| Partition | express | Priority interactive queue |

### Container Isolation

- **Apptainer** with fakeroot — user runs as themselves inside the container
- **Bind mounts** — only user's own data directory is mounted
- **No root access** — fakeroot provides user-namespace isolation only
- **UID preservation** — container UID matches host UID

### User Isolation

Each user gets:
- Separate Unix account inside the container
- Own `/home/<username>/` directory
- Own SLURM job with resource limits
- No access to other users' data directories

See `docs/TERMINAL_SLURM_SECURITY.md` for full security policy.

## HOME Directory

### Directory Structure

```
/home/<username>/
├── proj/
│   ├── <project-name>/       # Each project directory
│   │   ├── .agents/          # AI agent configs (auto-generated)
│   │   ├── .mcp.json         # Claude Code MCP server
│   │   ├── AGENTS.md         # Unified instructions for all AI tools
│   │   └── scitex/downloads/ # Paste/drop upload target
│   └── dotfiles/             # Git repo with shell configs (special project)
│       ├── .agents/          # AI agent configs (like any project)
│       ├── AGENTS.md
│       ├── bashrc
│       ├── bash_profile
│       ├── vimrc
│       ├── gitconfig
│       ├── screenrc
│       ├── ipython/
│       ├── install.sh
│       └── README.md
├── .bashrc -> proj/dotfiles/bashrc
├── .bash_profile -> proj/dotfiles/bash_profile
├── .vimrc -> proj/dotfiles/vimrc
├── .gitconfig -> proj/dotfiles/gitconfig
├── .screenrc -> proj/dotfiles/screenrc
├── .nvm/                     # Node Version Manager
├── .npm-global/              # npm global packages
├── .claude/                  # Claude Code user config
│   └── skills/scitex-hub/SKILL.md
├── .singularity/             # Apptainer cache
└── .ai-cli-installed         # Sentinel file
```

### Dotfiles Project

The **dotfiles** project (`is_home=True`) is a special project for managing
shell configurations:
- Auto-created on user signup and ensured on every login
- Always private — visibility is forced to `private` on save
- Cannot be deleted — `delete()` raises `ValueError`
- One per user — uniqueness enforced at model level
- Maps to `~/proj/dotfiles/` — a git-tracked repository containing
  bashrc, vimrc, gitconfig, and other shell configs
- Appears in the project selector and hub like any other project
- Gets full AI agent support (`.agents/`, `AGENTS.md`, `.mcp.json`)
  like any other project

### .bashrc

The bashrc (`~/proj/dotfiles/bashrc`) provides:

1. **Prompt**: `username@scitex:~/path $`
2. **AI CLI auto-install** (one-time on first login):
   - Installs nvm + Node.js 20
   - Installs claude, codex, gemini, agents globally
   - Creates `.ai-cli-installed` sentinel
3. **MCP config sync**: `agents sync --quiet` on every login
4. **`stx-show`**: Display images/plots in the browser via terminal escape sequences
5. **Aliases**: `ll`, `la`, `gs`, `ga`, `gc`, `gp`, `gl`, `python`, `pip`
6. **Auto-activate**: Sources `.venv/bin/activate` if present

The bashrc is managed as a git repo at `~/proj/dotfiles/`.
Users can edit and version-control their configuration.
A corruption detection mechanism (`_patch_bashrc_ai_tools()`) regenerates
the bashrc if required sections are missing or duplicated.

### Source Code

| File | Purpose |
|------|---------|
| `apps/console_app/services/terminal_broker/session.py` | `BasePTY`, `SessionState`, spawn/respawn |
| `apps/console_app/views/terminal/consumer.py` | WebSocket handler, broker client |
| `apps/console_app/views/terminal/workspace.py` | `ensure_workspace()`, directory setup |
| `apps/console_app/views/terminal/dotfiles.py` | Dotfiles repo creation + symlinks |
| `apps/console_app/services/agents_config.py` | AI agent config generation |
| `apps/accounts_app/signals.py` | Dotfiles project creation on signup |
| `apps/project_app/models/repository/project.py` | `is_home` field, delete protection |
