from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="clew",
        display_name="Clew - Pipeline DAG Editor",
        description=(
            "Computational pipeline design and execution using directed acyclic graphs (DAGs). "
            "Users create, chain, and run reproducible workflows with status tracking."
        ),
        tool_prefixes=["clew_"],
        capabilities=[
            "Create and edit pipeline chains",
            "Run pipelines with status tracking",
            "View pipeline statistics and results",
            "Generate Mermaid DAG visualizations",
        ],
        url_route="clew_app:clew_index",
        module_description=(
            "Pipeline DAG editor: create, chain, and run reproducible "
            "computational workflows with status tracking."
        ),
        mcp_tool_examples=["clew_run", "clew_chain", "clew_status"],
    )
)
