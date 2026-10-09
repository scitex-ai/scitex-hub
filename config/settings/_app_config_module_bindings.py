"""Read declared modules and a finite, source-only lazy forwarding contract.

No package, class, function or hook runs here. A physical child supplies only
Python's from-list fallback after proved attribute absence. Dotted attributes
need an actual declaration or a matched, untransformed module forwarder.
"""

from __future__ import annotations

import ast


class ModuleBindings:
    """Settings-private module references for the AppConfig declaration reader."""

    def __init__(self, declarations, find_module, bound_names, unavailable):
        self.declarations = declarations
        self.find_module = find_module
        self.bound_names = bound_names
        self.unavailable = unavailable

    def resolve(self, module, expression, lineage=()):
        if isinstance(expression, ast.Name):
            reference = (module, expression.id)
            if reference in lineage or len(lineage) >= 24:
                raise self.unavailable("AppConfig module alias is cyclic")
            lineage = (*lineage, reference)
            value = self.declarations.module(module).get(expression.id)
            if isinstance(value, self.unavailable):
                raise value
            if isinstance(value, tuple):
                initial = self._initializer_module(module, expression.id, value)
                if initial is not None:
                    return initial
                return self.from_import(*value, lineage)
            if isinstance(value, ast.Import):
                for alias in value.names:
                    if (alias.asname or alias.name.split(".")[0]) == expression.id:
                        return alias.name if alias.asname else alias.name.split(".")[0]
            if isinstance(value, (ast.Name, ast.Attribute)):
                return self.resolve(module, value, lineage)
        elif isinstance(expression, ast.Attribute):
            parent = self.resolve(module, expression.value, lineage)
            if parent is not None:
                return self.attribute(parent, expression.attr, lineage)
        return None

    def _initializer_module(self, parent, local, value):
        """Capture a literal child import before a later hook can change lookup."""
        if value[0] != parent:
            return None
        _, tree = self.declarations.source(parent)
        writes = [(node, origin) for node in tree.body
                  for name, origin in self.bound_names(node) if name == local]
        direct = [node for node, _ in writes if isinstance(node, ast.ImportFrom)
                  and node.level == 1 and node.module is None
                  and any((alias.asname or alias.name) == local and alias.name == value[1]
                          for alias in node.names)]
        if len(writes) != 1 or len(direct) != 1:
            raise self.unavailable("Relative module initializer binding is ambiguous")
        preceding = tree.body[:tree.body.index(direct[0])]
        bound = {name for node in preceding for name, _ in self.bound_names(node)}
        if value[1] in bound or "__getattr__" in bound:
            raise self.unavailable("Relative module initializer requires an earlier namespace effect")
        child = parent + "." + value[1]
        if self.find_module(child) is None:
            raise self.unavailable("Relative module initializer child is unavailable")
        return child

    def _declared(self, parent, symbol, lineage):
        _, tree = self.declarations.source(parent)
        names = {name for statement in tree.body for name, _ in self.bound_names(statement)}
        if symbol in names:
            return True, self.resolve(parent, ast.Name(id=symbol, ctx=ast.Load()), lineage)
        if "__getattr__" in names:
            target = self._lazy_export(parent, symbol, tree, lineage)
            return target is not None, target
        return False, None

    def from_import(self, parent, symbol, lineage=()):
        declared, target = self._declared(parent, symbol, lineage)
        if declared:
            return target
        child = parent + "." + symbol
        return child if self.find_module(child) is not None else None

    def attribute(self, parent, symbol, lineage=()):
        declared, target = self._declared(parent, symbol, lineage)
        if not declared or target is None:
            raise self.unavailable("AppConfig module attribute has no proven module binding")
        return target

    @staticmethod
    def _selector(test, argument, symbol):
        if (not isinstance(test, ast.Compare) or len(test.ops) != 1
            or not isinstance(test.left, ast.Name) or test.left.id != argument):
            return None
        right = test.comparators[0]
        if isinstance(test.ops[0], ast.Eq) and isinstance(right, ast.Constant) and isinstance(right.value, str):
            return symbol == right.value
        if isinstance(test.ops[0], ast.In) and isinstance(right, (ast.Set, ast.List, ast.Tuple)):
            if all(isinstance(value, ast.Constant) and isinstance(value.value, str) for value in right.elts):
                return symbol in {value.value for value in right.elts}
        return None

    @staticmethod
    def _attribute_error(statement, argument):
        if (not isinstance(statement, ast.Raise) or statement.cause is not None
            or not isinstance(statement.exc, ast.Call) or not isinstance(statement.exc.func, ast.Name)
            or statement.exc.func.id != "AttributeError" or len(statement.exc.args) != 1
            or statement.exc.keywords):
            return False
        value = statement.exc.args[0]
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return True
        return (isinstance(value, ast.JoinedStr) and all(
            (isinstance(part, ast.Constant) and isinstance(part.value, str))
            or (isinstance(part, ast.FormattedValue) and part.format_spec is None
                and isinstance(part.value, ast.Name) and part.value.id in {"__name__", argument})
            for part in value.values))

    @staticmethod
    def _module_argument(value, parent, argument, symbol):
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
        if isinstance(value, ast.JoinedStr):
            parts = []
            for part in value.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    parts.append(part.value)
                elif (isinstance(part, ast.FormattedValue) and part.conversion == -1
                      and part.format_spec is None and isinstance(part.value, ast.Name)
                      and part.value.id in {"__name__", argument}):
                    parts.append(parent if part.value.id == "__name__" else symbol)
                else:
                    return None
            return "".join(parts)
        return None

    @staticmethod
    def _initial_nodes(node):
        """Inspect evaluated initializer expressions, never function bodies."""
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            children = [*getattr(node, "decorator_list", []), *args.defaults,
                        *(value for value in args.kw_defaults if value is not None)]
            children += [arg.annotation for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                                                   *(arg for arg in (args.vararg, args.kwarg) if arg is not None)]
                         if arg.annotation is not None]
            if getattr(node, "returns", None) is not None:
                children.append(node.returns)
        else:
            children = ast.iter_child_nodes(node)
        for child in children:
            yield from ModuleBindings._initial_nodes(child)

    @staticmethod
    def _outer_function_nodes(node):
        """Inspect the current function scope, excluding nested scope bodies."""
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            # Definition expressions belong to the enclosing scope; bodies do
            # not make the enclosing hook a generator.
            children = [*getattr(node, "decorator_list", [])]
            if isinstance(node, ast.ClassDef):
                children += [*node.bases, *(item.value for item in node.keywords)]
            else:
                args = node.args
                children += [*args.defaults, *(value for value in args.kw_defaults if value is not None)]
                arguments = [*args.posonlyargs, *args.args, *args.kwonlyargs,
                             *(value for value in (args.vararg, args.kwarg) if value is not None)]
                children += [argument.annotation for argument in arguments if argument.annotation is not None]
                if getattr(node, "returns", None) is not None:
                    children.append(node.returns)
        else:
            children = ast.iter_child_nodes(node)
        for child in children:
            yield from ModuleBindings._outer_function_nodes(child)

    def _primitives(self, tree, hook, argument):
        module_imports, loading_sets = {}, {}
        for node in tree.body[:tree.body.index(hook)]:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "importlib":
                        module_imports[alias.asname or alias.name] = (node, "module")
            elif isinstance(node, ast.ImportFrom) and node.module == "importlib" and not node.level:
                for alias in node.names:
                    if alias.name == "import_module":
                        module_imports[alias.asname or alias.name] = (node, "function")
            elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call)
                  and isinstance(node.value.func, ast.Name) and node.value.func.id == "set"
                  and not node.value.args and not node.value.keywords):
                loading_sets[node.targets[0].id] = node
        primitive_names = {"globals", "set", "AttributeError", "__name__"}
        bound = {name for node in tree.body for name, _ in self.bound_names(node)}
        if primitive_names & bound or argument in {*primitive_names, *module_imports, *loading_sets}:
            raise self.unavailable("AppConfig module hook shadows a forwarding primitive")
        declarations = {id(node) for node, _ in module_imports.values()} | {id(node) for node in loading_sets.values()}
        protected = {*module_imports, *loading_sets}
        for name in protected:
            writes = [(node, origin) for node in tree.body
                      for key, origin in self.bound_names(node) if key == name]
            expected = module_imports[name][0] if name in module_imports else loading_sets[name]
            if len(writes) != 1 or writes[0][0] is not expected:
                raise self.unavailable("AppConfig forwarding primitive has a replacement binding")
        for statement in tree.body:
            if id(statement) in declarations:
                continue
            if any(isinstance(node, ast.Name) and node.id in protected
                   for node in self._initial_nodes(statement)):
                raise self.unavailable("AppConfig forwarding primitive has an initializer effect")
        local_writes = {}
        for statement in hook.body:
            for name, origin in self.bound_names(statement):
                local_writes.setdefault(name, []).append(origin)
        if {*primitive_names, argument, *loading_sets} & local_writes.keys():
            raise self.unavailable("AppConfig hook has a transformed lexical primitive")
        local_importers = {}
        for node in ast.walk(hook):
            if isinstance(node, ast.ImportFrom) and node.module == "importlib" and not node.level:
                for alias in node.names:
                    if alias.name == "import_module":
                        local_importers.setdefault(alias.asname or alias.name, []).append(alias)
        for name, origins in local_writes.items():
            if name in module_imports or name in local_importers:
                allowed = {id(alias) for alias in local_importers.get(name, [])}
                if not allowed or any(id(origin) not in allowed for origin in origins):
                    raise self.unavailable("AppConfig hook importer is lexically transformed")
        imports = {name + ".import_module" if kind == "module" else name
                   for name, (_, kind) in module_imports.items() if name not in local_writes}
        return imports, loading_sets

    @staticmethod
    def _bookkeeping(node, loading, argument, method):
        call = node.value if isinstance(node, ast.Expr) else None
        return (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and call.func.value.id == loading
                and call.func.attr == method and len(call.args) == 1
                and isinstance(call.args[0], ast.Name) and call.args[0].id == argument and not call.keywords)

    def _dispatch(self, body, argument, symbol, loading_sets):
        """Recognize the exact guarded/un guarded sequence, including termination."""
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]  # Only a leading docstring is inert.
        if not body or not self._attribute_error(body[-1], argument):
            raise self.unavailable("AppConfig module hook has no terminal literal absence")
        branches, loading = body[:-1], None
        if len(branches) == 3 and isinstance(branches[2], ast.Try):
            guard, enter, attempt = branches
            test = guard.test if isinstance(guard, ast.If) and not guard.orelse else None
            if (not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.In)
                or not isinstance(test.left, ast.Name) or test.left.id != argument
                or not isinstance(test.comparators[0], ast.Name) or test.comparators[0].id not in loading_sets
                or len(guard.body) != 1 or not self._attribute_error(guard.body[0], argument)):
                raise self.unavailable("AppConfig module loading guard is unproven")
            loading = test.comparators[0].id
            if (not self._bookkeeping(enter, loading, argument, "add") or attempt.handlers or attempt.orelse
                or len(attempt.finalbody) != 1
                or not self._bookkeeping(attempt.finalbody[0], loading, argument, "discard")):
                raise self.unavailable("AppConfig module loading cleanup is transformed")
            branches = attempt.body
        selected = []
        for node in branches:
            if not isinstance(node, ast.If) or node.orelse:
                raise self.unavailable("AppConfig module hook has unreachable or unsupported forwarding")
            match = self._selector(node.test, argument, symbol)
            if match is None:
                raise self.unavailable("AppConfig module hook has an unknown selector")
            if match:
                selected.append(node.body)
        if len(selected) > 1:
            raise self.unavailable("AppConfig module forwarders overlap")
        return selected[0] if selected else None, loading

    def _relative_module(self, parent, imported, symbol, loading, lineage):
        _, tree = self.declarations.source(parent)
        names = {name for node in tree.body for name, _ in self.bound_names(node)}
        if imported == symbol:
            if not loading or imported in names:
                raise self.unavailable("Recursive lazy module import has no proven loading refusal")
            # The exact initially empty loading guard rejects this same-name
            # recursive hasattr; Python then performs its from-list child import.
            child = parent + "." + imported
            return child if self.find_module(child) is not None else None
        return self.from_import(parent, imported, lineage)

    def _forwarded_case(self, parent, argument, symbol, body, imports, loading, lineage):
        modules, importers, cached = {}, set(imports), None
        if not body or not isinstance(body[-1], ast.Return):
            raise self.unavailable("Lazy module forwarder has no terminal return")
        for statement in body:
            if isinstance(statement, ast.ImportFrom):
                for alias in statement.names:
                    local = alias.asname or alias.name
                    if statement.level == 0 and statement.module == "importlib" and alias.name == "import_module":
                        importers.add(local)
                    elif statement.level == 1 and statement.module is None:
                        target = self._relative_module(parent, alias.name, symbol, loading, lineage)
                        if target is None:
                            raise self.unavailable("Lazy from-list export is not a proven module")
                        modules[local] = target
                    else:
                        raise self.unavailable("Lazy AppConfig import is not a literal module forwarder")
            elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target, value = statement.targets[0], statement.value
                if isinstance(target, ast.Name) and isinstance(value, ast.Call):
                    importer = isinstance(value.func, ast.Name) and value.func.id in importers
                    importer |= (isinstance(value.func, ast.Attribute) and value.func.attr == "import_module"
                                 and isinstance(value.func.value, ast.Name)
                                 and value.func.value.id + ".import_module" in importers)
                    name = (self._module_argument(value.args[0], parent, argument, symbol)
                            if importer and len(value.args) == 1 and not value.keywords else None)
                    if name is None or self.find_module(name) is None:
                        raise self.unavailable("Lazy AppConfig return is not a proven module import")
                    if target.id in modules:
                        raise self.unavailable("Lazy AppConfig module return binding is replaced")
                    modules[target.id] = name
                elif (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Call)
                      and isinstance(target.value.func, ast.Name) and target.value.func.id == "globals"
                      and not target.value.args and not target.value.keywords
                      and isinstance(target.slice, ast.Name) and target.slice.id == argument
                      and isinstance(value, ast.Name) and value.id in modules):
                    if cached is not None:
                        raise self.unavailable("Lazy AppConfig module cache is rewritten")
                    cached = value.id
                else:
                    raise self.unavailable("Lazy AppConfig forwarding binding is transformed")
            elif (statement is body[-1] and isinstance(statement, ast.Return)
                  and isinstance(statement.value, ast.Name) and statement.value.id in modules):
                if cached is not None and cached != statement.value.id:
                    raise self.unavailable("Lazy AppConfig cache and return identify different modules")
                return modules[statement.value.id]
            else:
                raise self.unavailable("Lazy AppConfig forwarding body is unsupported")
        raise self.unavailable("Lazy AppConfig forwarder has no module return")

    def _lazy_export(self, parent, symbol, tree, lineage):
        reference = (parent, "__getattr__:" + symbol)
        if reference in lineage or len(lineage) >= 24:
            raise self.unavailable("Lazy AppConfig module forwarding is cyclic")
        lineage = (*lineage, reference)
        hooks = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "__getattr__"]
        if len(hooks) != 1:
            raise self.unavailable("AppConfig module hook declaration is ambiguous")
        hook = hooks[0]
        if self.declarations.module(parent).get("__getattr__") is not hook:
            raise self.unavailable("AppConfig module hook binding is transformed")
        args = hook.args
        if (hook.decorator_list or args.posonlyargs or len(args.args) != 1 or args.vararg
            or args.kwarg or args.kwonlyargs or args.defaults or args.kw_defaults):
            raise self.unavailable("AppConfig module hook signature is unsupported")
        argument = args.args[0].arg
        if any(isinstance(node, (ast.Yield, ast.YieldFrom)) for statement in hook.body
               for node in self._outer_function_nodes(statement)):
            raise self.unavailable("AppConfig module hook returns a generator")
        imports, loading_sets = self._primitives(tree, hook, argument)
        body, loading = self._dispatch(hook.body, argument, symbol, loading_sets)
        if body is None:
            return None  # Proved hook absence; only from_import may try a child.
        return self._forwarded_case(parent, argument, symbol, body, imports, loading, lineage)
