from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="example",
        display_name="Examples - Interactive Demos",
        description=(
            "Interactive examples demonstrating scitex features including "
            "plotting, statistics, IO, and session management."
        ),
        capabilities=[
            "Run interactive plotting examples",
            "Explore statistics and data analysis demos",
            "Test IO and file format operations",
            "Session management demonstrations",
        ],
        page_patterns=["/example/"],
        url_prefix="/example/",
        module_description=(
            "Interactive examples demonstrating scitex features "
            "(plotting, stats, IO, sessions)."
        ),
    )
)
