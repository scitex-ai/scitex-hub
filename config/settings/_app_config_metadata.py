"""Read AppConfig identity declarations without importing settings or app bodies.

Django still creates and validates each accepted AppConfig during its normal
registry population. This settings-time reader only admits declarations whose
name, label and default selection can be established from Python source.
"""

from __future__ import annotations

import ast
import importlib.machinery
import sys
from dataclasses import dataclass
from pathlib import Path

from ._app_config_module_bindings import ModuleBindings


class MetadataUnavailable(ValueError):
    """The declared app identity cannot be established without execution."""


@dataclass(frozen=True)
class AppIdentity:
    name: str | None
    label: str | None
    default: bool | None = None
    base_config: bool = False


def _find_module(name):
    """Traverse finder paths without find_spec's parent-package imports."""
    if not isinstance(name, str) or any(not part.isidentifier() for part in name.split(".")):
        return None
    locations = sys.path
    prefix = []
    for part in name.split("."):
        prefix.append(part)
        spec = importlib.machinery.PathFinder.find_spec(".".join(prefix), locations)
        if spec is None:
            return None
        locations = spec.submodule_search_locations
        if locations is None and len(prefix) < len(name.split(".")):
            return None
    return spec


def _scope_nodes(node, *, class_bodies=False):
    """Visit declaration-time expressions, excluding function/lambda bodies."""
    yield node
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        children = [*getattr(node, "decorator_list", []), *node.args.defaults,
                    *(value for value in node.args.kw_defaults if value is not None)]
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        arguments += [value for value in (node.args.vararg, node.args.kwarg) if value is not None]
        children += [argument.annotation for argument in arguments if argument.annotation is not None]
        if getattr(node, "returns", None) is not None:
            children.append(node.returns)
    elif isinstance(node, ast.AnnAssign) and node.value is None:
        # A bare name annotation doesn't replace its current value. Inspect
        # annotation effects; other target forms remain conservative.
        children = [node.annotation]
        if not isinstance(node.target, ast.Name):
            children.append(node.target)
    elif isinstance(node, ast.ClassDef):
        children = [*node.decorator_list, *node.bases, *(item.value for item in node.keywords)]
        if class_bodies:
            children += node.body
    else:
        children = ast.iter_child_nodes(node)
    for child in children:
        yield from _scope_nodes(child, class_bodies=class_bodies)


def _bound_names(node):
    """Lexical writes in one scope, including definitions and import aliases."""
    for part in _scope_nodes(node):
        if isinstance(part, ast.Name) and isinstance(part.ctx, (ast.Store, ast.Del)):
            yield part.id, part
        elif isinstance(part, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            yield part.name, part
        elif isinstance(part, (ast.Import, ast.ImportFrom)):
            for alias in part.names:
                if alias.name == "*":
                    raise MetadataUnavailable("Star-imported AppConfig bindings cannot be proven")
                yield alias.asname or alias.name.split(".")[0], alias
        elif isinstance(part, ast.ExceptHandler) and part.name:
            yield part.name, part


def _namespace(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in {"locals", "globals", "vars"}
            and not node.args and not node.keywords)


def _refuse_rebound_references(tree):
    """Refuse later writes to names captured by earlier aliases/class bases."""
    captured = set()
    for node in _scope_nodes(tree):
        targets = []
        if isinstance(node, (ast.Assign, ast.Delete)):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.NamedExpr)):
            targets = [node.target]
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.optional_vars for item in node.items if item.optional_vars is not None]
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names = {node.name}
        elif isinstance(node, (ast.Import, ast.ImportFrom, ast.ExceptHandler)):
            names = {name for name, _ in _bound_names(node)}
        else:
            names = {name for target in targets for name, _ in _bound_names(target)}
        if names & captured:
            raise MetadataUnavailable("A captured AppConfig declaration reference is rebound")
        references = node.bases if isinstance(node, ast.ClassDef) else []
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, (ast.Name, ast.Attribute)):
            references = [*references, node.value]
        captured.update(part.id for reference in references for part in ast.walk(reference)
                        if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load))


def _refuse_namespace_effects(node, fields=None):
    """Refuse recognized identity effects even through aliases/other classes."""
    fields = {"name", "label", "default"} if fields is None else fields
    for part in _scope_nodes(node, class_bodies=True):
        if isinstance(part, ast.ClassDef):
            global_names = {name for statement in part.body for item in _scope_nodes(statement)
                            if isinstance(item, ast.Global) for name in item.names}
            writes = {name for statement in part.body for name, _ in _bound_names(statement)}
            if global_names & writes:
                raise MetadataUnavailable("An evaluated class body rebinds a module global")
        if (isinstance(part, ast.Attribute) and isinstance(part.ctx, (ast.Store, ast.Del))
            and part.attr in fields):
            raise MetadataUnavailable("AppConfig identity attribute is mutated")
        if isinstance(part, ast.Subscript) and isinstance(part.ctx, (ast.Store, ast.Del)) and _namespace(part.value):
            raise MetadataUnavailable("AppConfig declaration namespace is mutated")
        if isinstance(part, ast.Call):
            if (isinstance(part.func, ast.Name) and part.func.id in {"setattr", "delattr"}
                and len(part.args) >= 2 and (not isinstance(part.args[1], ast.Constant)
                    or part.args[1].value in fields)):
                raise MetadataUnavailable("AppConfig identity attribute is transformed")
            if (isinstance(part.func, ast.Attribute) and _namespace(part.func.value)
                and part.func.attr in {"update", "setdefault", "pop", "popitem", "clear",
                                       "__setitem__", "__delitem__"}):
                raise MetadataUnavailable("AppConfig declaration namespace is transformed")


class _Declarations:
    def __init__(self):
        self.modules = {}
        self.sources = {}
        self.module_bindings = ModuleBindings(self, _find_module, _bound_names, MetadataUnavailable)

    def source(self, name):
        if name in self.sources:
            return self.sources[name]
        spec = _find_module(name)
        if spec is None or spec.origin is None or not spec.origin.endswith(".py"):
            raise MetadataUnavailable("Python declaration source is unavailable")
        try:
            tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError) as error:
            raise MetadataUnavailable("Python declaration source is unreadable") from error
        _refuse_namespace_effects(tree)
        _refuse_rebound_references(tree)
        self.sources[name] = spec, tree
        return spec, tree

    def module(self, name):
        if name in self.modules:
            return self.modules[name]
        spec, tree = self.source(name)
        package = name if spec.submodule_search_locations is not None else name.rpartition(".")[0]

        def merge(branches):
            branches = [branch for branch in branches if branch is not None]
            if not branches:
                return None
            merged = {}
            for key in set().union(*(branch.keys() for branch in branches)):
                missing = MetadataUnavailable("Conditional AppConfig binding is unavailable")
                values = [branch.get(key, missing) for branch in branches]
                if all(value == values[0] for value in values):
                    merged[key] = values[0]
                else:
                    merged[key] = [part for value in values for part in
                                   (value if isinstance(value, list) else [value])]
            return merged

        def expressions(node, symbols):
            for part in _scope_nodes(node):
                if isinstance(part, ast.NamedExpr):
                    for key, _ in _bound_names(part.target):
                        symbols[key] = MetadataUnavailable("AppConfig binding uses an evaluated assignment")

        def collect(nodes, symbols):
            symbols = dict(symbols)
            for node in nodes:
                if isinstance(node, ast.Raise):
                    return None
                if isinstance(node, ast.If):
                    expressions(node.test, symbols)
                    symbols = merge([collect(node.body, symbols), collect(node.orelse, symbols)])
                elif isinstance(node, ast.Try):
                    success = collect(node.body, symbols)
                    branches = [collect(node.orelse, success) if success is not None else None]
                    for handler in node.handlers:
                        branch = dict(symbols)
                        if handler.name:
                            branch[handler.name] = handler  # An exception instance is not an AppConfig class.
                        branch = collect(handler.body, branch)
                        if branch is not None and handler.name:
                            branch.pop(handler.name, None)  # Python clears the exception alias.
                        branches.append(branch)
                    symbols = merge(branches)
                    if symbols is not None:
                        symbols = collect(node.finalbody, symbols)
                else:
                    expressions(node, symbols)
                    if isinstance(node, ast.ClassDef):
                        symbols[node.name] = node
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols[node.name] = (MetadataUnavailable("Decorated function binding is unprovable")
                                              if node.decorator_list else node)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            symbols[alias.asname or alias.name.split(".")[0]] = node
                    elif isinstance(node, ast.ImportFrom):
                        parent = package.split(".") if package else []
                        if node.level:
                            parent = parent[: len(parent) - node.level + 1]
                            module = ".".join([*parent, *([node.module] if node.module else [])])
                        else:
                            module = node.module
                        for alias in node.names:
                            if alias.name == "*":
                                raise MetadataUnavailable("Star-imported AppConfig bindings cannot be proven")
                            symbols[alias.asname or alias.name] = (module, alias.name)
                    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                        if isinstance(node, ast.AnnAssign) and node.value is None:
                            continue
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        for target in targets:
                            if isinstance(target, ast.Name):
                                expression = node.value
                                if (target.id in symbols and isinstance(expression, ast.Call)):
                                    expression = MetadataUnavailable("AppConfig binding has an unprovable replacement")
                                symbols[target.id] = expression
                            else:
                                for key, _ in _bound_names(target):
                                    symbols[key] = MetadataUnavailable("AppConfig binding uses an unsupported target")
                    else:
                        # Compound/augmented/deleted bindings are not guessed
                        # as either the old class or an absent class.
                        for key, _ in _bound_names(node):
                            symbols[key] = MetadataUnavailable("AppConfig binding is transformed")
                if symbols is None:
                    return None
            return symbols

        symbols = collect(tree.body, {})
        if symbols is None:
            raise MetadataUnavailable("AppConfig declaration does not reach population")
        self.modules[name] = symbols
        return symbols

    def identity(self, module, symbol, lineage=()):
        reference = (module, symbol)
        if reference in lineage or len(lineage) >= 24:
            raise MetadataUnavailable("AppConfig declaration inheritance is cyclic")
        if reference == ("django.apps", "AppConfig") or reference == ("django.apps.config", "AppConfig"):
            return AppIdentity(None, None, base_config=True)
        value = self.module(module).get(symbol)
        return self.value_identity(module, value, (*lineage, reference))

    def value_identity(self, module, value, lineage):
        if isinstance(value, MetadataUnavailable):
            raise value
        if isinstance(value, list):
            alternatives = [self.value_identity(module, item, lineage) for item in value]
            if any(item is not None for item in alternatives) and any(
                result is None and not (isinstance(item, ast.Constant) and item.value is None)
                for item, result in zip(value, alternatives, strict=True)
            ):
                raise MetadataUnavailable("AppConfig class alias has an unprovable replacement")
            alternatives = [item for item in alternatives if item is not None]
            identities = [(item.name, item.label, item.default) for item in alternatives]
            if identities and any(item != identities[0] for item in identities):
                raise MetadataUnavailable("Alternative AppConfig identities differ")
            return alternatives[0] if alternatives else None
        if isinstance(value, tuple):
            if self.module_bindings.from_import(*value, lineage) is not None:
                return None  # inspect.isclass excludes imported module objects.
            return self.identity(*value, lineage)
        if isinstance(value, ast.Name):
            return self.identity(module, value.id, lineage)
        if isinstance(value, ast.Attribute):
            imported_module = self.module_bindings.resolve(module, value.value, lineage)
            if imported_module is not None:
                return self.identity(imported_module, value.attr, lineage)
            raise MetadataUnavailable("AppConfig re-export module cannot be proven")
        if isinstance(value, ast.Constant) and value.value is None:
            return None
        if isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return None
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            if value.func.id == "type" and len(value.args) == 3 and "type" not in self.module(module):
                raise MetadataUnavailable("Dynamic AppConfig class construction cannot be proven")
            # A declared class invocation creates an instance, not an
            # AppConfig class candidate (e.g. django.conf.settings).
            if self.class_declaration(module, value.func.id):
                return None
        if not isinstance(value, ast.ClassDef):
            return None
        if value.decorator_list or value.keywords:
            raise MetadataUnavailable("AppConfig class declaration is transformed")
        parents = []
        for base in value.bases:
            if not isinstance(base, (ast.Name, ast.Attribute)):
                raise MetadataUnavailable("AppConfig base is not a declared class reference")
            parent = self.value_identity(module, base, lineage)
            if parent is None and (isinstance(base, ast.Attribute)
                                   or isinstance(self.module(module).get(base.id), ast.expr)):
                raise MetadataUnavailable("AppConfig base alias is not a declared class")
            if parent is not None:
                parents.append(parent)
        if not parents:
            return None
        if len(parents) != 1 or len(value.bases) != 1:
            raise MetadataUnavailable("AppConfig identity has multiple inheritance")
        fields = {"name": parents[0].name, "label": parents[0].label, "default": parents[0].default}
        for statement in value.body:
            targets = (statement.targets if isinstance(statement, ast.Assign)
                       else [statement.target] if isinstance(statement, ast.AnnAssign) else [])
            protected_fields = {*fields, "__slots__"}
            direct_fields = {id(target) for target in targets
                             if isinstance(target, ast.Name) and target.id in protected_fields}
            for field, origin in _bound_names(statement):
                if field in protected_fields and id(origin) not in direct_fields:
                    raise MetadataUnavailable("AppConfig identity field has an unsupported lexical binding")
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if statement.name in {*fields, "__new__", "__setattr__", "__getattribute__",
                                       "__getattr__", "__init_subclass__"}:
                    raise MetadataUnavailable("AppConfig identity attribute is transformed")
                if statement.name == "__init__":
                    args = statement.args
                    if (args.posonlyargs or len(args.args) != 1 or args.args[0].arg != "self"
                        or args.vararg is None or args.kwarg is None or args.kwonlyargs
                        or args.defaults or args.kw_defaults):
                        raise MetadataUnavailable("AppConfig constructor arguments are transformed")
                    for step in statement.body:
                        if isinstance(step, ast.Expr) and isinstance(step.value, ast.Constant):
                            continue
                        if isinstance(step, ast.Expr) and isinstance(step.value, ast.Call):
                            call = step.value
                            if (isinstance(call.func, ast.Attribute) and call.func.attr == "__init__"
                                and isinstance(call.func.value, ast.Call)
                                and isinstance(call.func.value.func, ast.Name) and call.func.value.func.id == "super"
                                and not call.func.value.args and not call.func.value.keywords
                                and len(call.args) == 1 and isinstance(call.args[0], ast.Starred)
                                and isinstance(call.args[0].value, ast.Name)
                                and call.args[0].value.id == args.vararg.arg
                                and len(call.keywords) == 1 and call.keywords[0].arg is None
                                and isinstance(call.keywords[0].value, ast.Name)
                                and call.keywords[0].value.id == args.kwarg.arg):
                                continue
                        if isinstance(step, (ast.Assign, ast.AnnAssign)) and isinstance(step.value, ast.Constant):
                            targets = step.targets if isinstance(step, ast.Assign) else [step.target]
                            if all(isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                                   and target.value.id == "self" and target.attr not in fields
                                   for target in targets):
                                continue
                        raise MetadataUnavailable("AppConfig constructor identity cannot be proven")
                continue
            if isinstance(statement, ast.Assign):
                names = [target.id for target in statement.targets if isinstance(target, ast.Name)]
                expression = statement.value
            elif isinstance(statement, ast.AnnAssign) and statement.value is None:
                continue
            elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                names, expression = [statement.target.id], statement.value
            else:
                continue
            if "__slots__" in names:
                slots = (expression.elts if isinstance(expression, (ast.Tuple, ast.List))
                         else [expression])
                if any(not isinstance(slot, ast.Constant) or not isinstance(slot.value, str)
                       or slot.value in fields for slot in slots):
                    raise MetadataUnavailable("AppConfig slots may transform identity attributes")
            for field in set(names) & fields.keys():
                if not isinstance(expression, ast.Constant):
                    raise MetadataUnavailable("AppConfig identity field is not literal")
                literal = expression.value
                if field == "default" and type(literal) is not bool:
                    raise MetadataUnavailable("AppConfig default field is not boolean")
                if field != "default" and not isinstance(literal, str):
                    raise MetadataUnavailable("AppConfig name or label is not a string")
                fields[field] = literal
        return AppIdentity(**fields)

    def class_declaration(self, module, symbol, lineage=()):
        """Prove a constructor expression's result is an instance, not a class."""
        reference = (module, symbol)
        if reference in lineage or len(lineage) >= 24:
            return False
        value = self.module(module).get(symbol)
        if isinstance(value, ast.ClassDef):
            return True
        if isinstance(value, tuple):
            return self.class_declaration(*value, (*lineage, reference))
        if isinstance(value, ast.Name):
            return self.class_declaration(module, value.id, (*lineage, reference))
        return False

    def selected(self, entry):
        if _find_module(entry) is None:
            module, separator, symbol = entry.rpartition(".")
            if not separator:
                raise MetadataUnavailable("AppConfig module is absent")
            identity = self.identity(module, symbol)
            if identity is None:
                raise MetadataUnavailable("Entry does not name a declared AppConfig")
        else:
            identity = AppIdentity(entry, None)
            configs = entry + ".apps"
            if _find_module(configs) is not None:
                candidates = []
                for symbol in self.module(configs):
                    candidate = self.identity(configs, symbol)
                    if candidate is not None and not candidate.base_config and candidate.default is not False:
                        candidates.append(candidate)
                if len(candidates) > 1:
                    candidates = [candidate for candidate in candidates if candidate.default is True]
                    if len(candidates) > 1:
                        raise MetadataUnavailable("Default AppConfig selection is ambiguous")
                if candidates:
                    identity = candidates[0]
        if not isinstance(identity.name, str) or not identity.name:
            raise MetadataUnavailable("AppConfig has no declared name")
        if _find_module(identity.name) is None:
            raise MetadataUnavailable("Declared app module is absent")
        label = identity.label if identity.label is not None else identity.name.rsplit(".", 1)[-1]
        if not isinstance(label, str) or not label.isidentifier():
            raise MetadataUnavailable("AppConfig label is invalid")
        return AppIdentity(identity.name, label, identity.default)


def app_config_identity(entry: str) -> AppIdentity:
    """Return a provable declared identity, leaving Django population unchanged."""
    return _Declarations().selected(entry)


def app_installation_entries(module: str) -> tuple[str, ...]:
    """Read the leaf's literal companion declaration without importing it.

    Absence preserves older plugins. Dynamic or malformed declarations cannot
    establish the installation contract and are refused before Django setup.
    """
    declarations = _Declarations()
    _, tree = declarations.source(module)
    if not any(
        (isinstance(node, ast.Name) and node.id == "INSTALLED_APPS_ENTRIES")
        or (isinstance(node, ast.alias)
            and (node.asname or node.name) == "INSTALLED_APPS_ENTRIES")
        or (isinstance(node, ast.Constant) and node.value == "INSTALLED_APPS_ENTRIES")
        for node in _scope_nodes(tree)
    ):
        return ()
    _refuse_namespace_effects(tree, {"INSTALLED_APPS_ENTRIES"})

    def resolve(name, symbol, lineage=()):
        reference = (name, symbol)
        if reference in lineage or len(lineage) >= 24:
            raise MetadataUnavailable("Companion declaration reference is cyclic")
        value = declarations.module(name).get(symbol)
        if value is None:
            if lineage:
                raise MetadataUnavailable("Companion declaration reference is absent")
            return ()
        if isinstance(value, tuple):
            return resolve(*value, (*lineage, reference))
        if isinstance(value, ast.Name):
            return resolve(name, value.id, (*lineage, reference))
        if not isinstance(value, ast.Tuple):
            raise MetadataUnavailable("INSTALLED_APPS_ENTRIES must be a literal tuple")
        entries = []
        for item in value.elts:
            if (not isinstance(item, ast.Constant) or not isinstance(item.value, str)
                or not item.value or any(not part.isidentifier() for part in item.value.split("."))):
                raise MetadataUnavailable("Companion paths must be plain Django app entries")
            entries.append(item.value)
        return tuple(entries)

    return resolve(module, "INSTALLED_APPS_ENTRIES")
