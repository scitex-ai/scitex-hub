"""
Export registered app skills for different consumers.

All context is derived from apps/*/skill.py registrations via
build_aggregated_context(). No hardcoded module lists or tool tables —
each app declares its own scope and the aggregator collects them.

Consumers:
- export_claude_skill() → SKILL.md for Claude Code terminal agents
- export_chat_prompt() → System prompt for browser-based chat LLM
"""

from .registry import build_aggregated_context, get_all_skills


def _build_skills_detail() -> str:
    """Build detailed skill sections (for Claude Code SKILL.md)."""
    skills = get_all_skills()
    if not skills:
        return "(No app skills registered yet — check apps/*/skill.py)\n"

    parts: list[str] = []
    for _name, skill in sorted(skills.items()):
        parts.append(f"### {skill.display_name}")
        parts.append("")
        parts.append(skill.description)
        parts.append("")
        if skill.page_patterns:
            patterns = ", ".join(f"`{p}`" for p in skill.page_patterns)
            parts.append(f"Active on pages: {patterns}")
            parts.append("")
        if skill.capabilities:
            for cap in skill.capabilities:
                parts.append(f"- {cap}")
            parts.append("")
        if skill.tool_prefixes:
            prefixes = ", ".join(f"`{p}*`" for p in skill.tool_prefixes)
            parts.append(f"MCP tool prefixes: {prefixes}")
            parts.append("")
    return "\n".join(parts)


def export_claude_skill() -> str:
    """Compile all registered app skills into a Claude Code SKILL.md.

    Returns:
        Markdown string in Claude Code skill format with YAML frontmatter.
    """
    parts = [
        "---",
        "name: scitex-hub",
        "description: SciTeX Hub research platform with MCP tools for "
        "plotting, statistics, literature management, manuscript writing, "
        "pipeline execution, and more.",
        "---",
        "",
        "# SciTeX Hub",
        "",
        "SciTeX Hub is a browser-based scientific research platform.",
        "You are running inside an Apptainer container with full terminal access.",
        "The `scitex` MCP server is connected.",
        "",
    ]

    # Aggregated from all apps/*/skill.py
    parts.append(build_aggregated_context())

    # Detailed skill descriptions (terminal agents benefit from full detail)
    parts.extend(
        [
            "## Registered App Skills (Detail)",
            "",
            _build_skills_detail(),
        ]
    )

    # Terminal-specific context
    parts.extend(
        [
            "## Terminal & Container (Apptainer)",
            "",
            "You run inside an **Apptainer (Singularity) container** with "
            "full user-space package management. You CAN install packages:",
            "",
            "### Pre-installed",
            "- **Python 3.11** with numpy, scipy, pandas, matplotlib, seaborn, "
            "plotly, scikit-learn, torch, transformers, jupyter",
            "- **Node.js 20** with claude-code, codex, gemini-cli, agents-dev",
            "- **System**: git, cmake, graphviz, screen, vim, nano, curl, wget",
            "- **Whisper.cpp** at /opt/whisper for speech-to-text",
            "",
            "### Installing Packages",
            "- `pip install <package>` or `uv pip install --system <package>` "
            "— install Python packages (no sudo needed)",
            "- `npm install -g <package>` — install Node.js packages globally",
            "- `apt-get install <package>` — install system packages "
            "(may require fakeroot or sudo depending on container mode)",
            "- All installed packages persist for the session duration",
            "",
            "### Environment",
            "- Terminal uses tmux for session persistence",
            "- `stx-show <file>` displays images/plots in the browser overlay",
            "- Project files are at `~/proj/{project_name}/`",
            "- Output from `@stx.session` goes to "
            "`script_out/FINISHED_SUCCESS/{session_id}/`",
            "",
            "## Quick Start",
            "",
            "```python",
            "import scitex as stx",
            "",
            "@stx.session",
            "def main(plt=stx.INJECTED, logger=stx.INJECTED):",
            "    fig, ax = stx.plt.subplots()",
            "    ax.plot_line(x, y)",
            '    stx.io.save(fig, "plot.png")  # Saves plot + CSV',
            "    return 0",
            "```",
            "",
        ]
    )

    return "\n".join(parts)


def export_chat_prompt() -> str:
    """Build a rich system prompt for the AI chat pane.

    Dynamically aggregated from all registered app skills — the same
    source of truth as export_claude_skill(), but tailored for the
    browser-based chat agent (no terminal/container info, adds media
    rendering guidance and UI interaction capabilities).

    Returns:
        Base system prompt string (active skill and page hints are
        appended by build_system_prompt() separately).
    """
    parts = [
        "You are an agentic scientific research assistant on SciTeX Hub. "
        "You have MCP tools — use them proactively to help the user. "
        "When asked to create plots, analyze data, or write files, "
        "DO IT immediately using your tools. Don't just describe what "
        "you would do — actually do it. "
        "Keep responses concise and compact — no lengthy greetings, "
        "no capability lists, no emoji-heavy formatting. "
        "Get straight to the point.",
        "",
        "## File Paths",
        "When the system prompt includes 'Project root path: /path/to/project', "
        "ALWAYS use that path as the base for output files. For example, if "
        "the project root is /app/data/users/alice/proj/demo, save a plot as "
        "/app/data/users/alice/proj/demo/my_plot.png (not just my_plot.png). "
        "This ensures files appear in the project and render inline in chat.",
        "",
        "## Media Rendering",
        "When MCP tools save files to the project directory, supported types "
        "are rendered inline in this chat automatically:",
        "- **Images** (.png, .jpg, .svg, .gif, .webp, .bmp) — displayed inline",
        "- **Audio** (.mp3, .wav, .ogg, .flac, .aac, .m4a) — playable inline",
        "- **Video** (.mp4, .webm, .avi, .mov) — playable inline",
        "- **CSV/TSV** — rendered as interactive tables (first 10 rows)",
        "- **PDF** — file link for download",
        "- **Mermaid diagrams** (.mmd, .mermaid) — rendered as diagrams",
        "- **Graphviz diagrams** (.dot, .gv) — rendered as diagrams",
        "Your response text is rendered as Markdown — use code blocks, "
        "headers, lists, and tables for clear formatting.",
        "",
        "## Execution Environment (Apptainer Container)",
        "Code execution (`project_exec_python`, `project_exec_shell`) runs "
        "inside an Apptainer container with Python 3.11, numpy, scipy, "
        "pandas, matplotlib, seaborn, plotly, scikit-learn, torch, "
        "transformers, graphviz, and more pre-installed. "
        "You CAN install additional packages with `pip install <package>` "
        "or `npm install -g <package>` — no sudo needed.",
        "",
        "## Browser UI Interaction",
        "You have a `ui_action` tool to drive the browser: navigate to "
        "pages, highlight elements, click buttons, fill inputs, and scroll. "
        "Use it for demos, tutorials, and helping users navigate the platform.",
        "",
    ]

    # Aggregated from all apps/*/skill.py — same source as terminal agents
    parts.append(build_aggregated_context())

    return "\n".join(parts)
