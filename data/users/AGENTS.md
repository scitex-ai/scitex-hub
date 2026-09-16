# home

SciTeX Hub project with access to 145+ MCP tools.

## Platform

You are running inside an Apptainer container on SciTeX Hub — a browser-based
scientific research platform. Python 3.11 and the `scitex` package are pre-installed.
The MCP server is connected.

## Web App Modules
- **Clew - Pipeline DAG Editor** (`/apps/clew/`) — Pipeline DAG editor: create, chain, and run reproducible computational workflows with status tracking.
- **Console - Development Environment** (`/apps/console/`) — Development environment: file browser, terminal (SLURM + Apptainer), code execution, Jupyter notebooks.
- **FigRecipe - Data Visualization** (`/apps/figrecipe/`) — Data visualization and figure management: view plots, manage figure recipes, export publication-ready figures.
- **Home - Project Hub** (`/apps/home/`) — Home page showing all user projects, activity feed, and quick actions.
- **Scholar - Literature Management** (`/apps/scholar/`) — Literature management: search papers (CrossRef/OpenAlex/Semantic Scholar), manage bibliography, explore citation graphs, download PDFs.
- **Store - App Catalog** (`/apps/store/`) — Browse, install, and publish community apps.
- **Tools - Shared Utilities** (`/apps/tools/`) — Shared utilities and tools for project management.
- **Workspace - Unified Layout** (`/apps/workspace/`) — Unified three-column layout: AI pane | worktree | module content. Modules switch without losing AI/worktree state.
- **Writer - Scientific Manuscript Editor** (`/apps/writer/`) — Scientific manuscript editor: LaTeX editing with live preview, figure/table management, bibliography, PDF compilation.

## Available Skills & Tools

- **Clew - Pipeline DAG Editor**: Create and edit pipeline chains, Run pipelines with status tracking, View pipeline statistics and results (tools: `clew_*`)
- **Console - Development Environment**: Browse and edit project files, Run terminal commands, Execute Python/Jupyter notebooks (tools: `project_*`, `introspect_*`, `template_*`)
- **FigRecipe - Data Visualization**: Create and edit plots via MCP tools, Compose multi-panel figures, Export publication-ready figures (tools: `plt_*`)
- **Home - Project Hub**: View all user projects, Activity feed and recent changes, Quick-navigate to any module
- **Scholar - Literature Management**: Search papers by keyword, DOI, or author, Manage bibliography (BibTeX import/export), Explore citation graphs (references and citations) (tools: `crossref_*`, `scholar_*`, `openalex_*`)
- **Store - App Catalog**: Browse and search community apps, Install and uninstall apps, Star and review apps
- **Tools - Shared Utilities**: File format converters, Project validators and linters, Utility functions and helpers
- **Workspace - Unified Layout**: 
- **Writer - Scientific Manuscript Editor**: Edit LaTeX manuscript sections, Compile manuscript to PDF, Manage figures and tables (tools: `writer_*`)

## MCP Tool Examples
| Module | Example Tools |
|--------|---------------|
| Clew | `clew_run`, `clew_chain`, `clew_status` |
| Console | `project_list_files`, `project_read_file`, `introspect_signature` |
| FigRecipe | `plt_plot`, `plt_compose`, `plt_crop` |
| Scholar | `scholar_search_papers`, `scholar_fetch_papers`, `crossref_search` |
| Writer | `writer_compile_manuscript`, `writer_add_figure`, `writer_add_bibentry` |

## Usage

```python
import scitex as stx

@stx.session
def main(plt=stx.INJECTED, logger=stx.INJECTED):
    stx.io.save(data, "results.csv")
    return 0
```

## MCP Tools

The `scitex` MCP server provides 145+ tools.
Run `agents sync` to push this config to your AI coding tool.
Run `/mcp` in Claude Code to list all available tools.
`stx-show <file>` in terminal displays images/plots in the browser.
