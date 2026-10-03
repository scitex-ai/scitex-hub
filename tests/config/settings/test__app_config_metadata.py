"""Settings-time identity reads must not execute application class bodies."""

from __future__ import annotations

import sys

import pytest

from config.settings._app_config_metadata import MetadataUnavailable, app_config_identity


@pytest.fixture
def declaration_package(tmp_path):
    """Real Python source with an import sentinel, rather than substituted APIs."""
    name = "app_identity_" + tmp_path.name.replace("-", "_")
    root = tmp_path / name
    root.mkdir()
    (root / "__init__.py").write_text("raise RuntimeError('parent imported')\n")
    sys.path.insert(0, str(tmp_path))
    try:
        yield name, root
    finally:
        sys.path.remove(str(tmp_path))


def _declarations(package, classes):
    name, root = package
    (root / "apps.py").write_text("from django.apps import AppConfig\n" + classes)
    return name


def test_class_body_settings_reads_are_not_executed(declaration_package):
    # Arrange
    name, root = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    default_auto_field = missing_lazy_settings.DEFAULT_AUTO_FIELD\n"
    ))
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, name, False)


def test_named_class_inherits_provable_name_and_label(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class Parent(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        "class Child(Parent):\n"
        "    default = False\n"
    )) + ".apps.Child"
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == (name, "declared_owner")


def test_explicit_default_wins_over_an_implicit_candidate(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class ImportedBase(AppConfig):\n"
        f"    name = {name!r}\n"
        "class DefaultConfig(ImportedBase):\n"
        "    default = True\n"
        "    label = 'selected_owner'\n"
    ))
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == (name, "selected_owner")


def test_multiple_implicit_candidates_keep_django_module_fallback(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class First(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'first'\n"
        "class Second(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'second'\n"
    ))
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == (name, name)


@pytest.mark.parametrize("field", [
    "name = str('dynamic')", "label = str('dynamic')", "default = bool(1)",
    "default = 1", "label = 'invalid-label'", "label += '_changed'",
    "if True:\n        label = 'conditional'",
])
def test_unprovable_identity_fields_are_refused(declaration_package, field):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'owner'\n"
        f"    {field}\n"
    ))
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_two_explicit_defaults_are_refused(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class First(AppConfig):\n"
        f"    name = {name!r}\n"
        "    default = True\n"
        "class Second(First):\n"
        "    default = True\n"
    ))
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_module_attribute_reexport_keeps_the_embedding_identity(declaration_package):
    # Arrange
    name, root = declaration_package
    (root / "embed.py").write_text(
        "from django.apps import AppConfig\n"
        "class HostConfig(AppConfig):\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self._manifest = None\n"
    )
    (root / "apps.py").write_text(
        f"from {name} import embed\n"
        "EmbeddingConfig = embed.HostConfig\n"
        "class EditorConfig(EmbeddingConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'embedded_editor'\n"
        "    default = True\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "embedded_editor", False)


def test_dynamic_class_alias_is_refused(declaration_package):
    # Arrange
    name, root = declaration_package
    (root / "apps.py").write_text(
        "from django.apps import AppConfig\n"
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "DefaultConfig = transform(DefaultConfig)\n"
    )
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


def test_constructor_cannot_change_the_population_arguments(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        super().__init__('different_owner', *args, **kwargs)\n"
    ))
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_identity_property_cannot_replace_an_inherited_literal(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class Parent(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        "class Child(Parent):\n"
        "    @property\n"
        "    def label(self):\n"
        "        return dynamic_label()\n"
    )) + ".apps.Child"
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_optional_absent_class_is_not_a_different_declared_identity(declaration_package):
    # Arrange
    name, root = declaration_package
    (root / "embed.py").write_text(
        "try:\n"
        "    from django.apps import AppConfig as HostConfig\n"
        "except ImportError:\n"
        "    HostConfig = None\n"
    )
    (root / "apps.py").write_text(
        f"from {name}.embed import HostConfig\n"
        "class EditorConfig(HostConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'optional_editor'\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label) == (name, "optional_editor")


def test_genuine_framework_config_keeps_its_declared_identity():
    # Arrange
    entry = "django.contrib.auth.apps.AuthConfig"
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == ("django.contrib.auth", "auth")


def test_genuine_account_config_metadata_is_settings_independent():
    # Arrange
    entry = "allauth.account"
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == ("allauth.account", "account")


def test_genuine_figrecipe_embedding_and_chat_configs_keep_their_owners():
    # Arrange
    entries = ["figrecipe._django", "figrecipe._django.apps.ScitexAppChatConfig"]
    # Act
    identities = [app_config_identity(entry) for entry in entries]
    # Assert
    assert [(item.name, item.label) for item in identities] == [
        ("figrecipe._django", "figrecipe_editor"), ("scitex_sdk.app._chat", "scitex_app")
    ]


def test_genuine_app_creator_default_remains_available():
    # Arrange
    entry = "scitex_sdk.creator"
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == ("scitex_sdk.creator", "scitex_sdk_creator")


@pytest.mark.parametrize("write", [
    "(name, label) = ('replacement', 'taken')",
    "[label] = ['taken']",
    "(other, (label,)) = (None, ('taken',))",
    "other = (label := 'taken')",
    "other = (name := 'replacement')",
    "locals()['label'] = 'taken'",
    "__slots__ = ('label',)",
    "__slots__ = ['name']",
    "__slots__ = get_slots()",
])
def test_nested_identity_writes_cannot_leave_stale_literals(declaration_package, write):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        f"    {write}\n"
    ))
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


@pytest.mark.parametrize("write", [
    "del DefaultConfig",
    "(DefaultConfig, other) = (AppConfig, None)",
    "[DefaultConfig] = [AppConfig]",
    "((DefaultConfig,), other) = ((AppConfig,), None)",
    "DefaultConfig.label = 'taken'",
    "DefaultConfig.name = 'replacement'",
    "DefaultConfig.label += '_changed'",
    "del DefaultConfig.label",
    "setattr(DefaultConfig, 'label', 'taken')",
    "other = (DefaultConfig := AppConfig)",
])
def test_module_writes_cannot_restore_a_stale_class_binding(declaration_package, write):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        f"{write}\n"
    ))
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_star_reexport_cannot_certify_a_module_fallback(declaration_package):
    # Arrange
    name, root = declaration_package
    (root / "other.py").write_text(
        "from django.apps import AppConfig\n"
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'reexported_owner'\n"
        "    default = True\n"
    )
    (root / "apps.py").write_text("from .other import *\n")
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


@pytest.mark.parametrize("hook", ["__init_subclass__", "__getattr__"])
def test_inherited_identity_hooks_are_not_executed_or_guessed(declaration_package, hook):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class Parent(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        f"    def {hook}(self, *args, **kwargs):\n"
        "        raise RuntimeError('identity hook executed')\n"
        "class Child(Parent):\n"
        "    label = 'child_owner'\n"
    )) + ".apps.Child"
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_subclass_named_AppConfig_is_selected_instead_of_the_base(declaration_package):
    # Arrange
    name, root = declaration_package
    (root / "apps.py").write_text(
        "from django.apps import AppConfig as DjangoAppConfig\n"
        "class AppConfig(DjangoAppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'selected_owner'\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "selected_owner", False)


def test_slots_cannot_mask_an_inherited_identity_literal(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class Parent(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        "class Child(Parent):\n"
        "    __slots__ = ('label',)\n"
    )) + ".apps.Child"
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_genuine_figrecipe_default_beats_its_embedding_reexport():
    # Arrange
    entries = ["figrecipe._django", "figrecipe._django.apps.FigRecipeEditorConfig"]
    # Act
    identities = [app_config_identity(entry) for entry in entries]
    # Assert
    assert [(item.name, item.label, item.default) for item in identities] == [
        ("figrecipe._django", "figrecipe_editor", True),
        ("figrecipe._django", "figrecipe_editor", True),
    ]


@pytest.mark.parametrize("replacement", [
    "def DefaultConfig():\n    pass",
    "async def DefaultConfig():\n    pass",
    "import types as DefaultConfig",
    "DefaultConfig = None",
])
def test_sequential_nonclass_binding_does_not_keep_the_old_class(declaration_package, replacement):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        f"{replacement}\n"
    ))
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, name, False)


@pytest.mark.parametrize("effect,suffix", [
    ("for DefaultConfig in [None]:\n    pass", "DefaultConfig"),
    ("with unexecuted_context() as DefaultConfig:\n    pass", "DefaultConfig"),
    ("try:\n    unexecuted_call()\nexcept Exception as DefaultConfig:\n    pass", "DefaultConfig"),
    ("for unused in [0]:\n    DefaultConfig.label = 'taken'", "DefaultConfig"),
    ("globals()['DefaultConfig'] = None", "DefaultConfig"),
    ("globals().update(DefaultConfig=None)", "DefaultConfig"),
    ("Alias = DefaultConfig\nAlias.label = 'taken'", "DefaultConfig"),
    ("def unused(value=setattr(DefaultConfig, 'label', 'taken')):\n    pass", "DefaultConfig"),
    ("def unused(value=(DefaultConfig := None)):\n    pass", "DefaultConfig"),
    ("class Other:\n    DefaultConfig.label = 'taken'", "DefaultConfig"),
    ("class Other:\n    def unused(self, value=setattr(DefaultConfig, 'label', 'taken')):\n        pass", "DefaultConfig"),
    ("class Child(DefaultConfig):\n    class label:\n        pass", "Child"),
    ("class Child(DefaultConfig):\n    import types as label", "Child"),
    ("class Child(DefaultConfig):\n    from types import SimpleNamespace as label", "Child"),
    ("class Child(DefaultConfig):\n    locals().update(label='taken')", "Child"),
    ("class Child(DefaultConfig):\n    def ready(self, value=(label := 'taken')):\n        pass", "Child"),
    ("class Child(DefaultConfig):\n    if True:\n        def label(self):\n            pass", "Child"),
])
def test_finite_evaluated_namespace_effects_are_refused_for_explicit_entries(declaration_package, effect, suffix):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        f"{effect}\n"
    )) + ".apps." + suffix
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(entry)


def test_unevaluated_function_body_does_not_mutate_declared_identity(declaration_package):
    # Arrange
    name, _ = declaration_package
    entry = _declarations(declaration_package, (
        "class DefaultConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'declared_owner'\n"
        "def unused():\n"
        "    DefaultConfig.label = 'not_executed'\n"
    ))
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label) == (name, "declared_owner")


def test_optional_import_none_is_an_alternative_not_a_sequential_replacement(declaration_package):
    # Arrange
    name, root = declaration_package
    (root / "embed.py").write_text(
        "try:\n"
        "    from django.apps import AppConfig as HostConfig\n"
        "except ImportError:\n"
        "    HostConfig = None\n"
    )
    (root / "apps.py").write_text(
        f"from {name}.embed import HostConfig\n"
        "class DefaultConfig(HostConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'optional_owner'\n"
    )
    # Act
    identity = app_config_identity(name)
    # Assert
    assert (identity.name, identity.label) == (name, "optional_owner")


@pytest.mark.parametrize("body", [
    "Alias = DefaultConfig\nDefaultConfig = None",
    "class Child(DefaultConfig):\n    default = True\nclass DefaultConfig:\n    pass",
    "class Other:\n    global DefaultConfig\n    DefaultConfig = None",
    "DefaultConfig = None\nDynamicConfig = type('DynamicConfig', (AppConfig,), {'name': 'OWNER_MODULE', 'label': 'dynamic_owner'})",
])
def test_captured_references_and_type_construction_are_refused(declaration_package, body):
    # Arrange: the real stdlib future feature is also a proven instance.
    name, root = declaration_package
    (root / "apps.py").write_text(
        "from __future__ import annotations\nfrom django.apps import AppConfig\n"
        f"class DefaultConfig(AppConfig):\n    name = {name!r}\n    label = 'declared_owner'\n" + body.replace("OWNER_MODULE", name) + "\n"
    )
    # Act / Assert
    with pytest.raises(MetadataUnavailable):
        app_config_identity(name)


@pytest.mark.parametrize("body,suffix", [
    ("DefaultConfig: object", ""),
    ("class Child(DefaultConfig):\n    default = True\n    label: object", "Child"),
    ("instance = DefaultConfig('OWNER_MODULE', None)", ""),
    ("pass", ""),
])
def test_annotations_and_proven_instances_preserve_identity(declaration_package, body, suffix):
    # Arrange: the real stdlib future feature is also a proven instance.
    name, root = declaration_package
    (root / "apps.py").write_text(
        "from __future__ import annotations\nfrom django.apps import AppConfig\n"
        f"class DefaultConfig(AppConfig):\n    name = {name!r}\n    label = 'declared_owner'\n" + body.replace("OWNER_MODULE", name) + "\n"
    )
    entry = name + ".apps." + suffix if suffix else name
    # Act
    identity = app_config_identity(entry)
    # Assert
    assert (identity.name, identity.label, name in sys.modules) == (name, "declared_owner", False)
