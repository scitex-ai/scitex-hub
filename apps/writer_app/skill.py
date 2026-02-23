from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="writer",
        display_name="Writer - Scientific Manuscript Editor",
        description=(
            "LaTeX manuscript editing, compilation, and figure/table management. "
            "Users write scientific papers with real-time LaTeX preview, "
            "bibliography integration, and structured sections."
        ),
        tool_prefixes=["writer_"],
        capabilities=[
            "Edit LaTeX manuscript sections",
            "Compile manuscript to PDF",
            "Manage figures and tables",
            "Handle bibliography entries",
            "Export to various formats (PDF, Overleaf)",
            "Manage claims and cross-references",
        ],
        page_patterns=["/writer/"],
    )
)
