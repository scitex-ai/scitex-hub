"""Skill registration for Agentic Journal."""

from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="scitex_agentic_journal_hub_app",
        display_name="Agentic Journal",
        description="ARA-native open publishing with AI review",
        capabilities=[
            "View Agentic Journal content",
            "Interact with Agentic Journal workspace",
        ],
        page_patterns=["/scitex_agentic_journal_hub_app/"],
        url_prefix="/scitex_agentic_journal_hub_app/",
        app_description="ARA-native open publishing with AI review",
    )
)
