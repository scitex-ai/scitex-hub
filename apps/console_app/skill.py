from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="console",
        display_name="Console - Development Environment",
        description=(
            "File management, terminal access, and code execution. "
            "Users manage project files, run scripts, and interact with their workspace. "
            "Supports Jupyter notebooks and has full terminal access via SLURM + Apptainer."
        ),
        tool_prefixes=["project_", "introspect_", "template_"],
        capabilities=[
            "Browse and edit project files",
            "Run terminal commands",
            "Execute Python/Jupyter notebooks",
            "Manage project templates",
            "Introspect Python modules and APIs",
        ],
        page_patterns=["/console/", "/files/"],
        url_prefix="/console/",
        module_description=(
            "Development environment: file browser, terminal (SLURM + Apptainer), "
            "code execution, Jupyter notebooks."
        ),
        mcp_tool_examples=[
            "project_list_files",
            "project_read_file",
            "introspect_signature",
        ],
    )
)
