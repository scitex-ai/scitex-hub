from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="appmaker",
        display_name="App Maker - Custom Apps",
        description=(
            "Create, edit, and manage custom workspace modules. "
            "Build new modules using the template system."
        ),
        capabilities=[
            "Create modules from templates",
            "Edit module source code",
            "Preview and test modules",
            "Publish to apps catalog",
        ],
        page_patterns=["/appmaker/"],
        url_prefix="/appmaker/",
        module_description=("Create, edit, and manage custom workspace modules."),
    )
)
