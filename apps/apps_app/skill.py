from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="marketplace",
        display_name="Marketplace - Module Catalog",
        description=(
            "Browse, install, and publish community modules. "
            "Discover extensions created by other users."
        ),
        capabilities=[
            "Browse and search community modules",
            "Install and uninstall modules",
            "Star and review modules",
            "Publish custom modules",
        ],
        page_patterns=["/marketplace/"],
        url_prefix="/marketplace/",
        module_description=("Browse, install, and publish community modules."),
    )
)
