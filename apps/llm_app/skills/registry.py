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
