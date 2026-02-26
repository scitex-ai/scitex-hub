from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="modulemaker",
        display_name="Module Maker - Custom Modules",
        description=(
            "Create, edit, and manage custom workspace modules. "
            "Build new modules using the template system."
        ),
        capabilities=[
            "Create modules from templates",
            "Edit module source code",
            "Preview and test modules",
            "Publish to marketplace",
        ],
        page_patterns=["/modulemaker/"],
        url_prefix="/modulemaker/",
        module_description=("Create, edit, and manage custom workspace modules."),
    )
)
