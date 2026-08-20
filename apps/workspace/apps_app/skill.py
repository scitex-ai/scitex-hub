from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="store",
        display_name="Store - App Catalog",
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
        url_route="apps_app:browse",
        module_description=("Browse, install, and publish community apps."),
    )
)
