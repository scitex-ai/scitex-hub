"""Real declaration sources distinguish module bindings from nearby files."""

from __future__ import annotations

import sys

import pytest

from config.settings._app_config_metadata import MetadataUnavailable, app_config_identity


@pytest.fixture
def module_package(tmp_path):
    name = "module_exports_" + tmp_path.name.replace("-", "_")
    root = tmp_path / name
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "api.py").write_text(
        "from django.apps import AppConfig\n"
        "class HostConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'module_export_owner'\n"
        "    default = True\n"
    )
    sys.path.insert(0, str(tmp_path))
    try:
        yield name, root
    finally:
        sys.path.remove(str(tmp_path))


@pytest.mark.parametrize("source", [
    "from . import api as ns\n",
    "import importlib\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        globals()[name] = module\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "_LOADING = set()\n"
    "def __getattr__(name):\n"
    "    if name in _LOADING:\n"
    "        raise AttributeError('loading')\n"
    "    _LOADING.add(name)\n"
    "    try:\n"
    "        if name == 'ns':\n"
    "            from . import api as imported\n"
    "            return imported\n"
    "    finally:\n"
    "        _LOADING.discard(name)\n"
    "    raise AttributeError('missing')\n",
])
def test_declared_and_literal_lazy_module_exports_keep_the_owner(module_package, source):
    # Arrange
    name, root = module_package
    (root / "__init__.py").write_text(source)
    (root / "apps.py").write_text(
        f"from {name} import ns\n"
        "class EditorConfig(ns.HostConfig):\n"
        "    default = True\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "module_export_owner", False)


def test_unbound_dotted_attribute_is_not_supplied_by_a_nearby_file(module_package):
    # Arrange
    name, root = module_package
    (root / "apps.py").write_text(
        f"import {name} as namespace\n"
        "class EditorConfig(namespace.api.HostConfig):\n"
        "    default = True\n"
    )
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


@pytest.mark.parametrize("source", [
    "def __getattr__(name):\n    return DynamicConfig\n",
    "def __getattr__(name):\n"
    "    if name == 'ns':\n        return DynamicConfig\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "importlib = transformed_importer\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "def __getattr__(name):\n"
    "    raise AttributeError(transform_namespace())\n",
])
def test_unknown_hook_outputs_cannot_hide_a_class_or_infer_a_module(module_package, source):
    # Arrange
    name, root = module_package
    (root / "ns.py").write_text((root / "api.py").read_text())
    (root / "__init__.py").write_text(source)
    (root / "apps.py").write_text(f"from {name} import ns\n")
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


@pytest.mark.parametrize("source", [
    "import importlib\n"
    "def __getattr__(name):\n"
    "    \"\"\"Forward declared modules without running their bodies here.\"\"\"\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        globals()[name] = module\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "_LOADING = set()\n"
    "def __getattr__(name):\n"
    "    \"\"\"The genuine SDK guarded relative forwarding shape.\"\"\"\n"
    "    if name in _LOADING:\n"
    "        raise AttributeError('loading')\n"
    "    _LOADING.add(name)\n"
    "    try:\n"
    "        if name == 'ns':\n"
    "            from . import ns as imported\n"
    "            return imported\n"
    "    finally:\n"
    "        _LOADING.discard(name)\n"
    "    raise AttributeError('missing')\n",
])
def test_leading_docstring_and_guarded_same_name_forwarding_keep_the_owner(module_package, source):
    # Arrange
    name, root = module_package
    (root / "ns.py").write_text((root / "api.py").read_text())
    (root / "__init__.py").write_text(source)
    (root / "apps.py").write_text(
        f"from {name} import ns\n"
        "class EditorConfig(ns.HostConfig):\n"
        "    default = True\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "module_export_owner", False)


def test_relative_initializer_keeps_its_module_before_a_later_hook(module_package):
    # Arrange
    name, root = module_package
    (root / "other.py").write_text((root / "api.py").read_text().replace("module_export_owner", "later_hook_owner"))
    (root / "__init__.py").write_text(
        "from . import api as ns\n"
        "import importlib\n"
        "def __getattr__(name):\n"
        "    if name == 'api':\n"
        "        module = importlib.import_module(f'{__name__}.other')\n"
        "        return module\n"
        "    raise AttributeError('missing')\n"
    )
    (root / "apps.py").write_text(
        f"from {name} import ns\n"
        "class EditorConfig(ns.HostConfig):\n"
        "    default = True\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "module_export_owner", False)


def test_proved_hook_absence_allows_only_the_from_list_child_fallback(module_package):
    # Arrange
    name, root = module_package
    (root / "unlisted.py").write_text((root / "api.py").read_text())
    (root / "__init__.py").write_text(
        "import importlib\n"
        "def __getattr__(name):\n"
        "    if name == 'ns':\n"
        "        module = importlib.import_module(f'{__name__}.api')\n"
        "        return module\n"
        "    raise AttributeError('missing')\n"
    )
    (root / "apps.py").write_text(
        f"from {name} import unlisted\n"
        "class EditorConfig(unlisted.HostConfig):\n"
        "    default = True\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "module_export_owner", False)


def test_dotted_lookup_does_not_apply_a_missing_hook_from_list_fallback(module_package):
    # Arrange
    name, root = module_package
    (root / "unlisted.py").write_text((root / "api.py").read_text())
    (root / "__init__.py").write_text(
        "import importlib\n"
        "def __getattr__(name):\n"
        "    if name == 'ns':\n"
        "        module = importlib.import_module(f'{__name__}.api')\n"
        "        return module\n"
        "    raise AttributeError('missing')\n"
    )
    (root / "apps.py").write_text(
        f"import {name} as namespace\n"
        "class EditorConfig(namespace.unlisted.HostConfig):\n"
        "    default = True\n"
    )
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


@pytest.mark.parametrize("source", [
    "import importlib\n"
    "def __getattr__(name):\n"
    "    raise AttributeError('blocked')\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "from django.apps import AppConfig\n"
    "class api(AppConfig):\n"
    "    name = 'parent_class'\n"
    "    label = 'real_parent_class'\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        from . import api as imported\n"
    "        return imported\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "importlib.import_module = replacement\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "setattr(importlib, 'import_module', replacement)\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "importlib.__dict__['import_module'] = replacement\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "alias = importlib\n"
    "alias.import_module = replacement\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "__name__ = 'different_package'\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "def __getattr__(importlib):\n"
    "    if importlib == 'ns':\n"
    "        module = importlib.import_module('module_exports.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        from . import api as globals\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        globals()[name] = module\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "        from . import api as importlib\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        from . import api as __name__\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "_LOADING = set()\n"
    "_LOADING.add('ns')\n"
    "def __getattr__(name):\n"
    "    if name in _LOADING:\n"
    "        raise AttributeError('loading')\n"
    "    _LOADING.add(name)\n"
    "    try:\n"
    "        if name == 'ns':\n"
    "            module = importlib.import_module(f'{__name__}.api')\n"
    "            return module\n"
    "    finally:\n"
    "        _LOADING.discard(name)\n"
    "    raise AttributeError('missing')\n",
    "import importlib\n"
    "from other_module import importlib\n"
    "def __getattr__(name):\n"
    "    if name == 'ns':\n"
    "        module = importlib.import_module(f'{__name__}.api')\n"
    "        return module\n"
    "    raise AttributeError('missing')\n",
])
def test_unreachable_class_exports_and_transformed_primitives_refuse(module_package, source):
    # Arrange
    name, root = module_package
    (root / "ns.py").write_text((root / "api.py").read_text())
    (root / "__init__.py").write_text(source)
    (root / "apps.py").write_text(f"from {name} import ns\n")
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


def test_missing_initializer_child_is_not_created_by_a_later_hook(module_package):
    # Arrange
    name, root = module_package
    (root / "__init__.py").write_text(
        "from . import missing as ns\n"
        "import importlib\n"
        "def __getattr__(name):\n"
        "    if name == 'missing':\n"
        "        module = importlib.import_module(f'{__name__}.api')\n"
        "        return module\n"
        "    raise AttributeError('missing')\n"
    )
    (root / "apps.py").write_text(f"from {name} import ns\n")
    assert not (root / "missing.py").exists()
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


@pytest.mark.parametrize("generator_expression", ["yield None", "yield from ()"])
def test_unselected_outer_generator_branch_cannot_certify_a_module(module_package, generator_expression):
    # Arrange
    name, root = module_package
    (root / "__init__.py").write_text(
        "import importlib\n"
        "def __getattr__(name):\n"
        "    if name == 'ns':\n"
        "        module = importlib.import_module(f'{__name__}.api')\n"
        "        return module\n"
        "    if name == 'other':\n"
        f"        {generator_expression}\n"
        "    raise AttributeError('missing')\n"
    )
    (root / "apps.py").write_text(f"from {name} import ns\n")
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)
