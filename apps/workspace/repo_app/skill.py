from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="hub",
        display_name="Home - Project Hub",
        description=(
            "Home page showing all user projects, activity feed, "
            "and quick actions. Entry point for navigating to other modules."
        ),
        capabilities=[
            "View all user projects",
            "Activity feed and recent changes",
            "Quick-navigate to any module",
            "Create new projects",
        ],
        url_route="repo_app:index",
        module_description=(
            "Home page showing all user projects, activity feed, and quick actions."
        ),
    )
)
