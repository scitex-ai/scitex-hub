#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What hub DECLARES: the floors it asks for, and the imports it performs.

This half runs on the deploy host and reads the repository. It is deliberately
the only half that reads the repository -- everything about what is *installed*
comes from ``preflight_probe.py`` running inside the target, because reading a
version on the host and stating it about production is the exact mistake that
took scitex.ai down on 2026-08-18.

Two readers live here.

``declared_floors`` parses pyproject. It reads ``[project] dependencies`` AND the
named ``[project.optional-dependencies]`` groups, because prod installs
``.[all]`` (Dockerfile.prod: ``uv pip install --system --no-cache ".[all]"``) and
the existing static guard in tests/deployment reads only the base ``dependencies``
array -- which silently misses scitex-ui, figrecipe and scitex-cards, all of which
live in optional groups.

``module_scope_sibling_imports`` walks the repo's Python with ``ast`` and reports
every sibling import that executes at MODULE scope, split into unguarded and
try/except-guarded. Module scope is the crash-loop surface: an unguarded one that
fails does not degrade a feature, it stops Django from starting. A guarded one is
reported but never fatal -- that is what the guard is for, and treating it as
fatal would make the gate red on ``scitex_live_paper``, which is deliberately
absent in prod today.

No third-party imports. The deploy host is not guaranteed to have ``packaging``
or a Python new enough for ``tomllib``, and a preflight that cannot run is a
preflight that gets removed from the deploy path.
"""

import ast
import os
import re

#: ``"pkg>=1.2.3",`` as one entry of a pyproject dependency array.
_ARRAY_ENTRY = re.compile(r'^\s*"([A-Za-z0-9_.\-\[\]]+(?:[^"]*)?)"\s*,?\s*(?:#.*)?$')

#: ``name >= 1.2.3, < 2`` -- distribution name, optional extras, specifier tail.
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$")


class DeclarationError(Exception):
    """The repository could not be read. Never downgraded to an empty result."""


def canonical(name):
    """PEP 503 canonical distribution name, so ``scitex_ui`` == ``scitex-ui``."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


class Floor(object):
    """One declared requirement, with the pyproject line it came from."""

    def __init__(self, name, specifier, line_number, group):
        self.name = canonical(name)
        self.specifier = specifier.strip()
        self.line_number = line_number
        self.group = group

    def __repr__(self):
        return "Floor({0}{1} @ pyproject.toml:{2} [{3}])".format(
            self.name, self.specifier, self.line_number, self.group
        )

    @property
    def declaration(self):
        return "{0}{1}".format(self.name, self.specifier)


def _array_bounds(lines, header):
    """Line range of a ``<header> = [`` ... ``]`` array, or ``None``.

    Scans to a line that is exactly ``]``. Using the first ``]`` in the text
    instead stops inside a COMMENT -- this pyproject's prose mentions ``[all]``
    and ``[django]`` -- which truncates the array to nothing and makes every
    comparison vacuously green.
    """
    start = None
    for index, line in enumerate(lines):
        if line.strip() == header + " = [":
            start = index
            break
    if start is None:
        return None
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == "]":
            return (start + 1, index)
    raise DeclarationError("unterminated array '{0} = [' in pyproject.toml".format(header))


def _parse_requirement(text):
    """``("scitex-writer", ">=2.42.0")`` from ``"scitex-writer>=2.42.0"``."""
    match = _REQUIREMENT.match(text)
    if not match:
        return None
    name, _extras, tail = match.groups()
    tail = (tail or "").split(";")[0].strip()  # drop environment markers
    return canonical(name), tail


def declared_floors(pyproject_path, extras=()):
    """Every requirement hub declares, keyed by canonical distribution name.

    ``extras`` names the ``[project.optional-dependencies]`` groups to include.
    Prod installs ``.[all]``, so the deploy path passes ``("all",)``.
    """
    if not os.path.isfile(pyproject_path):
        raise DeclarationError("pyproject not found: {0}".format(pyproject_path))
    lines = open(pyproject_path, encoding="utf-8").read().splitlines()

    sections = [("dependencies", "dependencies")]
    for extra in extras:
        sections.append((extra, "extra:" + extra))

    floors = {}
    for header, group in sections:
        bounds = _array_bounds(lines, header)
        if bounds is None:
            if group == "dependencies":
                raise DeclarationError("no 'dependencies = [' array in {0}".format(pyproject_path))
            raise DeclarationError(
                "no '{0} = [' array in {1}; the extra hub's image installs does not exist "
                "under that name".format(header, pyproject_path)
            )
        for index in range(bounds[0], bounds[1]):
            stripped = lines[index].strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = _ARRAY_ENTRY.match(lines[index])
            if not match:
                continue
            parsed = _parse_requirement(match.group(1))
            if parsed is None:
                continue
            name, specifier = parsed
            if not specifier:
                continue  # an unpinned dependency declares no floor to check
            # First declaration wins so the reported line number is the one a
            # reader will find; a later, looser repeat cannot weaken it.
            if name not in floors:
                floors[name] = Floor(name, specifier, index + 1, group)
    return floors


class SiblingImport(object):
    """One module-scope sibling import found in hub's own source."""

    def __init__(self, module, path, line_number, guarded):
        self.module = module
        self.path = path
        self.line_number = line_number
        self.guarded = guarded

    @property
    def where(self):
        return "{0}:{1}".format(self.path, self.line_number)

    def __repr__(self):
        return "SiblingImport({0} @ {1}{2})".format(
            self.module, self.where, " guarded" if self.guarded else ""
        )


def _is_sibling(module, roots, prefixes, ignored):
    top = module.split(".")[0]
    if top in ignored:
        return False
    if top in roots:
        return True
    return any(module.startswith(prefix) or top.startswith(prefix.rstrip(".")) for prefix in prefixes)


class _Scanner(ast.NodeVisitor):
    """Walks one module, tracking whether we are at module scope and guarded.

    Function bodies are NOT module scope: they run on request, so a failure there
    is a broken endpoint, not a boot loop. Class bodies ARE module scope -- they
    execute at import time. try/except that names ImportError (or bare Exception)
    marks everything inside its ``try`` as guarded.
    """

    def __init__(self, path, predicate):
        self.path = path
        self._predicate = predicate
        self.found = []
        self._module_scope = True
        self._guard_depth = 0

    def _record(self, module, node):
        if not self._module_scope or module is None:
            return
        if self._predicate(module):
            self.found.append(
                SiblingImport(module, self.path, node.lineno, self._guard_depth > 0)
            )

    def visit_Import(self, node):
        for alias in node.names:
            self._record(alias.name, node)

    def visit_ImportFrom(self, node):
        if node.level:  # relative import -- hub's own package, never a sibling
            return
        self._record(node.module, node)

    def _visit_out_of_scope(self, node):
        was = self._module_scope
        self._module_scope = False
        self.generic_visit(node)
        self._module_scope = was

    visit_FunctionDef = _visit_out_of_scope
    visit_AsyncFunctionDef = _visit_out_of_scope
    visit_Lambda = _visit_out_of_scope

    def visit_Try(self, node):
        guards = False
        for handler in node.handlers:
            names = []
            if isinstance(handler.type, ast.Name):
                names = [handler.type.id]
            elif isinstance(handler.type, ast.Tuple):
                names = [e.id for e in handler.type.elts if isinstance(e, ast.Name)]
            elif handler.type is None:
                names = ["BaseException"]
            if {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"} & set(names):
                guards = True
        if guards:
            self._guard_depth += 1
        for statement in node.body:
            self.visit(statement)
        if guards:
            self._guard_depth -= 1
        for handler in node.handlers:
            self.generic_visit(handler)
        for statement in node.orelse + node.finalbody:
            self.visit(statement)


def module_scope_sibling_imports(repo_root, contract):
    """Every sibling module hub imports at module scope, deduplicated.

    Returns ``(imports, files_scanned)``. ``files_scanned`` is the control: an
    empty result and a scanner that read nothing are indistinguishable without
    it, and this repository has already been bitten by exactly that shape.
    """
    roots = set(contract.get("sibling_import_roots", []))
    prefixes = tuple(contract.get("sibling_import_root_prefixes", []))
    ignored = set(contract.get("ignore_import_roots", []))

    def predicate(module):
        return _is_sibling(module, roots, prefixes, ignored)

    seen = {}
    files_scanned = 0
    for scan_dir in contract.get("scan_dirs", []):
        base = os.path.join(repo_root, scan_dir)
        if not os.path.isdir(base):
            raise DeclarationError(
                "scan directory {0} does not exist; the import scan would be vacuous".format(base)
            )
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [
                d for d in dirnames
                if d not in {"__pycache__", "node_modules", ".git", "migrations"}
            ]
            for filename in sorted(filenames):
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    source = open(path, encoding="utf-8", errors="replace").read()
                    tree = ast.parse(source, filename=path)
                except SyntaxError:
                    continue
                files_scanned += 1
                scanner = _Scanner(os.path.relpath(path, repo_root), predicate)
                scanner.visit(tree)
                for item in scanner.found:
                    previous = seen.get(item.module)
                    # An unguarded occurrence dominates: one unguarded import is
                    # enough to stop Django booting no matter how many guarded
                    # ones exist elsewhere.
                    if previous is None or (previous.guarded and not item.guarded):
                        seen[item.module] = item
    return sorted(seen.values(), key=lambda i: i.module), files_scanned

# EOF
