from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="tools",
        display_name="Tools - Shared Utilities",
        description=(
            "Shared utilities and tools for project management, "
            "including converters, validators, and helper functions."
        ),
        capabilities=[
            "File format converters",
            "Project validators and linters",
            "Utility functions and helpers",
        ],
        page_patterns=["/tools/"],
        url_prefix="/tools/",
        module_description=("Shared utilities and tools for project management."),
    )
)
