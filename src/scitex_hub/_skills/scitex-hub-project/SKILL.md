---
name: scitex-hub-project
description: SciTeX Hub project management — CRUD plus secure MCP handlers for list, read, write, search, and execute within project sandboxes.
user-invocable: false
---

# scitex-hub: Project Management

`scitex_hub.project` covers project lifecycle (CRUD) and the sandboxed
file-operation handlers that back the MCP project tools. All file operations
are constrained to `ALLOWED_DATA_ROOT` with path-traversal protection. The
umbrella `scitex.project` re-exports this surface.

## Sub-skills

| File | Description |
|------|-------------|
| [01_mcp-file-ops.md](01_mcp-file-ops.md) | list_files, read_file, write_file, search_files, exec_python, exec_shell handlers; security model |

## Project CRUD

```python
from scitex_hub.project import (
    project_list, project_create, project_delete, project_rename,
)

projects = project_list()
new = project_create("my-project", description="My research")
```

## File-operation handlers (async)

```python
from scitex_hub.project._mcp.handlers import (
    list_files_handler, read_file_handler, write_file_handler,
    search_files_handler, exec_python_handler, exec_shell_handler,
)
import asyncio

result = asyncio.run(list_files_handler("/app/data/users/alice/proj"))
```
