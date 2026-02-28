from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="apps",
        display_name="Apps - App Catalog",
        description=(
            "Browse, install, and publish community apps. "
            "Discover extensions created by other users."
        ),
        capabilities=[
            "Browse and search community apps",
            "Install and uninstall apps",
            "Star and review apps",
            "Publish custom apps",
        ],
        page_patterns=["/apps/"],
        url_prefix="/apps/",
        module_description=("Browse, install, and publish community apps."),
    )
)
