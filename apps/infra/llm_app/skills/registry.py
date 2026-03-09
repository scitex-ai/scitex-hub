from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Skill dataclass
# ---------------------------------------------------------------------------


@dataclass
class Skill:
    app_name: str
    display_name: str
    description: str
    tool_prefixes: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    page_patterns: list[str] = field(default_factory=list)
    # Module metadata for system prompt generation
    url_prefix: str = ""
    module_description: str = ""
    mcp_tool_examples: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_registry: dict[str, Skill] = {}


def register(skill: Skill) -> None:
    """Register a skill. Called from each app's skill.py."""
    _registry[skill.app_name] = skill


def get_skill(app_name: str) -> Skill | None:
    return _registry.get(app_name)


def get_skill_for_page(page: str) -> Skill | None:
    """Find skill matching a page URL pattern."""
    for skill in _registry.values():
        for pattern in skill.page_patterns:
            if pattern in page or page.startswith(pattern.rstrip("/")):
                return skill
    return None


def get_all_skills() -> dict[str, Skill]:
    return dict(_registry)


def build_aggregated_context() -> str:
    """Aggregate all registered skills into structured prompt sections.

    Each app's skill.py declares its own scope (module_description,
    capabilities, tool_prefixes, mcp_tool_examples). This function
    collects them into a coherent context block for LLM consumption.
    """
    skills = get_all_skills()
    if not skills:
        return ""

    parts: list[str] = []

    # Web app modules — from each skill's url_prefix + module_description
    modules = [
        (s.url_prefix, s.display_name, s.module_description)
        for s in skills.values()
        if s.url_prefix and s.module_description
    ]
    if modules:
        parts.append("## Web App Modules")
        for url, name, desc in sorted(modules):
            parts.append(f"- **{name}** (`{url}`) — {desc}")
        parts.append("")

    # All skills summary
    parts.append("## Available Skills & Tools")
    parts.append("")
    for _name, skill in sorted(skills.items()):
        caps = ", ".join(skill.capabilities[:3]) if skill.capabilities else ""
        prefixes = ", ".join(f"`{p}*`" for p in skill.tool_prefixes)
        line = f"- **{skill.display_name}**: {caps}"
        if prefixes:
            line += f" (tools: {prefixes})"
        parts.append(line)
    parts.append("")

    # MCP tool examples table — from each skill's mcp_tool_examples
    examples = [
        (s.display_name.split(" - ")[0].strip(), s.mcp_tool_examples)
        for s in skills.values()
        if s.mcp_tool_examples
    ]
    if examples:
        parts.append("## MCP Tool Examples")
        parts.append("| Module | Example Tools |")
        parts.append("|--------|---------------|")
        for name, tools in sorted(examples):
            tools_str = ", ".join(f"`{t}`" for t in tools[:3])
            parts.append(f"| {name} | {tools_str} |")
        parts.append("")

    return "\n".join(parts)


def build_system_prompt(
    skill: Skill | None,
    base_prompt: str,
    page_hints: list[str] | None = None,
) -> str:
    """Build enhanced system prompt with skill context."""
    parts = [base_prompt]
    if skill:
        parts.append(f"\n## Current App: {skill.display_name}\n{skill.description}")
        if skill.capabilities:
            parts.append("\n### Available Capabilities:")
            for cap in skill.capabilities:
                parts.append(f"- {cap}")
        if skill.tool_prefixes:
            parts.append(
                f"\n### Prioritized Tool Prefixes: {', '.join(skill.tool_prefixes)}"
            )
    if page_hints:
        parts.append("\n### Page Elements:")
        for hint in page_hints:
            parts.append(f"- {hint}")
    return "\n".join(parts)
