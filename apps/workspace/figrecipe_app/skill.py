from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="figrecipe",
        display_name="FigRecipe - Data Visualization",
        description=(
            "Data visualization and figure management. View plots, manage "
            "figure recipes, and export publication-ready figures."
        ),
        tool_prefixes=["plt_"],
        capabilities=[
            "Create and edit plots via MCP tools",
            "Compose multi-panel figures",
            "Export publication-ready figures",
            "Manage figure recipes (pltz/figz formats)",
        ],
        page_patterns=["/apps/figrecipe/"],
        url_prefix="/apps/figrecipe/",
        module_description=(
            "Data visualization and figure management: view plots, "
            "manage figure recipes, export publication-ready figures."
        ),
        mcp_tool_examples=["plt_plot", "plt_compose", "plt_crop"],
    )
)
