"""
Export registered app skills as Claude Code skill files.

Compiles all apps/*/skill.py registrations into a single SKILL.md
suitable for placement in .claude/skills/scitex-cloud/.
"""

from .registry import get_all_skills


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
        "SciTeX Cloud is a browser-based scientific research platform. The `scitex` MCP server",
        "provides tools for the full research workflow: data analysis, visualization, statistics,",
        "literature search, manuscript writing, and reproducible pipelines.",
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
        "## Available Modules",
        "",
    ]

    for name, skill in sorted(skills.items()):
        parts.append(f"### {skill.display_name}")
        parts.append("")
        parts.append(skill.description)
        parts.append("")
        if skill.capabilities:
            for cap in skill.capabilities:
                parts.append(f"- {cap}")
            parts.append("")
        if skill.tool_prefixes:
            prefixes = ", ".join(f"`{p}*`" for p in skill.tool_prefixes)
            parts.append(f"MCP tool prefixes: {prefixes}")
            parts.append("")

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

    return "\n".join(parts)
