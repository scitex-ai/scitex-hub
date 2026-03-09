from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="hub",
        display_name="Dashboard - Project Hub",
        description=(
            "Project dashboard showing all user projects, activity feed, "
            "and quick actions. Entry point for navigating to other modules."
        ),
        capabilities=[
            "View all user projects",
            "Activity feed and recent changes",
            "Quick-navigate to any module",
            "Create new projects",
        ],
        page_patterns=["/"],
        url_prefix="/",
        module_description=(
            "Project dashboard showing all user projects, activity feed, "
            "and quick actions."
        ),
    )
)
