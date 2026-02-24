"""
Export registered app skills as Claude Code skill files.

Compiles all apps/*/skill.py registrations into a single SKILL.md
suitable for placement in .claude/skills/scitex-cloud/.

Includes:
- Registered app skills (capabilities, tool prefixes)
- Web app structure (URL patterns, module descriptions)
- Platform navigation guidance
- MCP tool interaction patterns
"""

from .registry import get_all_skills

# ---------------------------------------------------------------------------
# Web app module descriptions — dynamically enriches the SKILL.md
# These are keyed by URL prefix and describe each major web app module.
# When a new app is added, add an entry here so the agent knows about it.
# ---------------------------------------------------------------------------
_WEB_APP_MODULES = {
    "/hub/": {
        "name": "Hub",
        "description": "Project dashboard showing all user projects, activity feed, and quick actions.",
    },
    "/scholar/": {
        "name": "Scholar",
        "description": "Literature management: search papers (CrossRef/OpenAlex/Semantic Scholar), manage bibliography, explore citation graphs, download PDFs.",
    },
    "/console/": {
        "name": "Console",
        "description": "Development environment: file browser, terminal (SLURM + Apptainer), code execution, Jupyter notebooks.",
    },
    "/writer/": {
        "name": "Writer",
        "description": "Scientific manuscript editor: LaTeX editing with live preview, figure/table management, bibliography, PDF compilation.",
    },
    "/workspace/": {
        "name": "Workspace",
        "description": "Unified three-column layout: AI pane (left) | worktree (middle) | module content (right). Modules switch without losing AI/worktree state.",
    },
    "/vis/": {
        "name": "Visualizer",
        "description": "Data visualization and figure management: view plots, manage figure recipes, export publication-ready figures.",
    },
    "/clew/": {
        "name": "Clew",
        "description": "Pipeline DAG editor: create, chain, and run reproducible computational workflows with status tracking.",
    },
    "/marketplace/": {
        "name": "Marketplace",
        "description": "Discover and install community-shared templates, pipelines, and tools.",
    },
    "/modulemaker/": {
        "name": "Module Maker",
        "description": "Create custom scitex modules from templates with guided setup.",
    },
    "/example/": {
        "name": "Examples",
        "description": "Interactive examples demonstrating scitex features (plotting, stats, IO, sessions).",
    },
}


def export_claude_skill() -> str:
    """Compile all registered app skills into a Claude Code SKILL.md.

    Returns:
        Markdown string in Claude Code skill format with YAML frontmatter.
    """
    skills = get_all_skills()

    parts = [
        "---",
        "name: scitex-cloud",
        "description: SciTeX Cloud research platform with 145+ MCP tools for plotting, statistics, literature management, manuscript writing, pipeline execution, and more.",
        "---",
        "",
        "# SciTeX Cloud",
        "",
        "SciTeX Cloud is a browser-based scientific research platform.",
        "You are running inside an Apptainer container with full terminal access.",
        "The `scitex` MCP server is connected and provides 145+ tools.",
        "",
    ]

    # ── Web App Structure ──────────────────────────────────────
    parts.extend(
        [
            "## Web App Structure",
            "",
            "The platform is organized into modules, each at a URL prefix.",
            "Projects follow GitHub-style URLs: `/{username}/{project}/`.",
            "",
        ]
    )

    for url, mod in sorted(_WEB_APP_MODULES.items()):
        parts.append(f"- **{mod['name']}** (`{url}`) — {mod['description']}")
    parts.append("")

    parts.extend(
        [
            "### Navigation",
            "",
            "- Tab bar at top switches between modules (Hub, Scholar, Console, Writer, etc.)",
            "- Workspace layout: AI pane (left) | worktree file tree (middle) | module content (right)",
            "- AI pane has three modes: Chat (LLM), Console (terminal), Jobs (SLURM)",
            "- Double-click AI panel header to toggle between Chat and Console",
            "- `Alt+A` toggles the AI panel open/closed",
            "",
        ]
    )

    # ── Registered App Skills ──────────────────────────────────
    parts.extend(
        [
            "## Registered App Skills",
            "",
        ]
    )

    if skills:
        for name, skill in sorted(skills.items()):
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
    else:
        parts.extend(
            [
                "(No app skills registered yet — check apps/*/skill.py)",
                "",
            ]
        )

    # ── Quick Start ────────────────────────────────────────────
    parts.extend(
        [
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

    # ── Key Patterns ───────────────────────────────────────────
    parts.extend(
        [
            "## Key Patterns",
            "",
            "- `stx.io.save(obj, path)` — universal save (30+ formats, auto CSV for figures)",
            "- `stx.io.load(path)` — universal load",
            "- `stx.stats.test_*(g1, g2)` — 23 statistical tests with effect sizes and power",
            "- `stx.plt.subplots()` — publication-ready figures with data tracking",
            "- `@stx.session` — reproducible experiment tracking with auto-CLI",
            "",
        ]
    )

    # ── MCP Tools ──────────────────────────────────────────────
    parts.extend(
        [
            "## MCP Tools",
            "",
            "The `scitex` MCP server provides tools organized by group:",
            "",
            "| Group | Description | Example Tools |",
            "|-------|-------------|---------------|",
            "| PLT | Plotting & figures | `plt_plot`, `plt_compose`, `plt_crop` |",
            "| STATS | Statistical tests | `stats_run_test`, `stats_power_analysis` |",
            "| SCHOLAR | Literature search | `scholar_search_papers`, `scholar_fetch_papers` |",
            "| WRITER | Manuscript editing | `writer_compile_manuscript`, `writer_add_figure` |",
            "| CLEW | Pipeline execution | `clew_run`, `clew_chain`, `clew_status` |",
            "| DIAGRAM | Mermaid/Graphviz | `plt_diagram_create`, `plt_diagram_render` |",
            "| INTROSPECT | Python API inspection | `introspect_signature`, `introspect_source` |",
            "| TEMPLATE | Project templates | `template_clone_template` |",
            "| DATASET | Research datasets | `dataset_search`, `dataset_db_build` |",
            "| AUDIO | Text-to-speech | `audio_speak` |",
            "| CAPTURE | Screenshots | `capture_capture_screenshot` |",
            "",
            "Run `/mcp` in Claude Code to list all available tools.",
            "",
        ]
    )

    # ── Terminal Interaction ────────────────────────────────────
    parts.extend(
        [
            "## Terminal & Container",
            "",
            "- You run inside an Apptainer container with Python 3.11, scitex, and AI CLI tools",
            "- Terminal uses tmux for session persistence",
            "- `stx-show <file>` displays images/plots in the browser overlay",
            "- Project files are at `~/proj/{project_name}/`",
            "- Output from `@stx.session` goes to `script_out/FINISHED_SUCCESS/{session_id}/`",
            "",
        ]
    )

    return "\n".join(parts)
