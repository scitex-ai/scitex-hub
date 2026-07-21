"""Skill registration for Live Paper."""

from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="scitex_live_paper_hub_app",
        display_name="Live Paper",
        description="Interactive paper viewer with M4 re-review chip",
        capabilities=["View Live Paper content", "Interact with Live Paper workspace"],
        page_patterns=["/scitex_live_paper_hub_app/"],
        url_prefix="/scitex_live_paper_hub_app/",
        app_description="Interactive paper viewer with M4 re-review chip",
    )
)
