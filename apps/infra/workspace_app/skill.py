from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="workspace",
        display_name="Workspace - Unified Layout",
        description=(
            "Unified three-column layout: AI pane (left) | worktree file tree "
            "(middle) | module content (right). Modules switch without losing "
            "AI or worktree state."
        ),
        url_route="workspace_app:shell",
        module_description=(
            "Unified three-column layout: AI pane | worktree | module content. "
            "Modules switch without losing AI/worktree state."
        ),
    )
)
