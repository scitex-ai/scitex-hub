"""Keep legacy deep bindings fixed while admitting literal public Writer consumers."""

import ast
from pathlib import Path

import pytest

# Existing wrapper migration debt only. New consumers get no filename exemption.
GRANDFATHERED_SCITEX_WRITER_IMPORTERS = frozenset(
    {
        "apps/workspace/writer_app/urls/writer_django.py",
        "apps/workspace/writer_app/views/editor/api/compilation_full_job.py",
        "apps/workspace/writer_app/views/overleaf/api.py",
        "apps/workspace/writer_app/services/compiler.py",
        "apps/workspace/writer_app/services/writer/compilation.py",
        "apps/infra/project_app/views/projects/live_viewer.py",
        "apps/infra/project_app/services/writer_workspace_layout.py",
    }
)


def _writer_imports(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".")[0] == "scitex_writer"
        ):
            found.append(node)
        elif isinstance(node, ast.Import) and any(
            alias.name.split(".")[0] == "scitex_writer" for alias in node.names
        ):
            found.append(node)
        elif isinstance(node, ast.Call) and node.args:
            literal = node.args[0]
            if not isinstance(literal, ast.Constant) or not isinstance(
                literal.value, str
            ):
                continue
            if literal.value.split(".")[0] != "scitex_writer":
                continue
            function = node.func
            if (
                isinstance(function, ast.Name)
                and function.id == "__import__"
                or isinstance(function, ast.Attribute)
                and function.attr == "import_module"
            ):
                found.append(node)
    return found


def _public_writer_only(imports):
    return bool(imports) and all(
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "scitex_writer"
        and [(alias.name, alias.asname) for alias in node.names] == [("Writer", None)]
        for node in imports
    )


def test_new_hub_consumers_use_the_literal_public_writer_port():
    root = Path(__file__).resolve().parents[4]
    found = {}
    for base in ("apps", "config"):
        for path in (root / base).rglob("*.py"):
            source = path.read_text()
            if "scitex_writer" not in source:
                continue
            imports = _writer_imports(source)
            if imports:
                found[path.relative_to(root).as_posix()] = imports
    assert GRANDFATHERED_SCITEX_WRITER_IMPORTERS <= found.keys()
    unauthorized = [
        path
        for path, imports in found.items()
        if path not in GRANDFATHERED_SCITEX_WRITER_IMPORTERS
        and not _public_writer_only(imports)
    ]
    assert unauthorized == [], unauthorized


def test_literal_public_writer_coordination_is_admitted():
    source = "from scitex_writer import Writer\nw = Writer(path, git_strategy=None)\nw.read_section('abstract')"
    assert _public_writer_only(_writer_imports(source))


@pytest.mark.parametrize(
    "source",
    [
        "import scitex_writer",
        "from scitex_writer._writer import Writer",
        "from scitex_writer import ensure_workspace",
        "from scitex_writer import Writer, ensure_workspace",
        "from scitex_writer import *",
        "from scitex_writer import Writer as Alternate",
        "__import__('scitex_writer._writer')",
        "importlib.import_module('scitex_writer._writer')",
    ],
)
def test_unproven_or_deep_writer_bindings_are_refused(source):
    assert not _public_writer_only(_writer_imports(source))
