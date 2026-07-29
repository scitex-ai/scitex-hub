"""Skill registry — the in-product assistant's map of the app surface.

A skill declares WHICH ROUTE is its landing page, never WHERE that route is
mounted. The mount is derived from the live URLconf at read time, so the URL
the assistant hands a user cannot drift from ``config/urls.py``.

Declaring the prefix as a literal is what broke this before: eight of eleven
apps advertised paths that had become 301 redirects, and one advertised a path
with no mount behind it at all. Retyping the literals would have re-armed the
same trap, so the literal is gone rather than corrected.
"""

import sys
from dataclasses import dataclass, field

from django.urls import NoReverseMatch, reverse

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
    # Reversible route name for this app's landing page, e.g.
    # "scholar_app:index". The mount prefix is DERIVED from this via
    # reverse() — see resolve_url(). Leave empty for an app with no page.
    url_route: str = ""
    module_description: str = ""
    mcp_tool_examples: list[str] = field(default_factory=list)

    def resolve_url(self) -> str | None:
        """Landing URL for this app, resolved against the live URLconf.

        Returns ``None`` when the app declares no route, or declares one that
        does not resolve (not mounted / renamed). ``None`` means "do not
        advertise this app" — never a guessed root mount, because a guess is
        indistinguishable from a correct answer at the point it is consumed.

        reverse() also applies SCRIPT_NAME, which a hardcoded literal cannot.
        """
        if not self.url_route:
            return None
        try:
            return reverse(self.url_route)
        except NoReverseMatch:
            return None

    @property
    def url_prefix(self) -> str:
        """Derived mount prefix; empty string when the app is not mounted."""
        return self.resolve_url() or ""

    @property
    def page_patterns(self) -> list[str]:
        """Derived page match patterns.

        Previously hand-declared alongside url_prefix, which meant the same
        stale string existed twice and a half-fix would leave the assistant
        attaching the wrong app's capabilities to a page.
        """
        url = self.resolve_url()
        return [url] if url else []


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_registry: dict[str, Skill] = {}
# app_name -> module that registered it, so a re-import of the SAME skill.py
# (Django autoreload) is allowed while a genuine collision is not.
_registry_source: dict[str, str] = {}


class DuplicateSkillError(ValueError):
    """Two different apps claimed the same ``app_name``.

    Its own type so skill discovery can re-raise it instead of folding it into
    a generic warning — a collision silently drops one app from the
    assistant's map, which is the failure mode this guard exists to catch.
    """


def register(skill: Skill) -> None:
    """Register a skill. Called from each app's skill.py.

    Raises on a duplicate ``app_name`` from a different module. Two apps once
    shipped byte-identical skill.py files both claiming ``app_name="tools"``;
    the second silently replaced the first, so one app was simply absent from
    the assistant's map with nothing to show for it.
    """
    source = sys._getframe(1).f_globals.get("__name__", "<unknown>")
    previous = _registry_source.get(skill.app_name)
    if previous is not None and previous != source:
        raise DuplicateSkillError(
            f"duplicate skill app_name {skill.app_name!r}: already registered "
            f"by {previous!r}, now again by {source!r}. Each app must claim a "
            f"unique app_name — rename one of them, or delete the duplicate "
            f"skill.py if it is a copy."
        )
    _registry[skill.app_name] = skill
    _registry_source[skill.app_name] = source


def get_skill(app_name: str) -> Skill | None:
    return _registry.get(app_name)


def get_skill_for_page(page: str) -> Skill | None:
    """Find the skill whose mount prefix best matches ``page``.

    Longest match wins. The previous first-match-over-dict-order let an app
    mounted at "/" claim every page in the product, so which app's
    capabilities the assistant loaded depended on registration order.
    """
    best_len = -1
    best: Skill | None = None
    for skill in _registry.values():
        url = skill.resolve_url()
        if not url:
            continue
        if page == url or page.startswith(url) or page.rstrip("/") == url.rstrip("/"):
            score = len(url.rstrip("/"))
            if score > best_len:
                best_len, best = score, skill
    return best


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

    # Web app modules — URL derived from the live URLconf, never declared.
    # An app that does not resolve is omitted rather than advertised: telling
    # a user to visit a dead path is worse than not mentioning the app.
    modules = [
        (url, s.display_name, s.module_description)
        for s in skills.values()
        for url in [s.resolve_url()]
        if url and s.module_description
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
