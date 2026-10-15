"""Operator/developer command surface under ``scitex-hub dev``."""

import json
from importlib import import_module
from pathlib import Path

import pytest
from click.testing import CliRunner

from scitex_hub._cli.main import main


def test_root_help_lists_dev_operator_group():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "dev" in result.output


def test_dev_help_lists_setup_domains():
    result = CliRunner().invoke(main, ["dev", "--help"])

    assert result.exit_code == 0
    assert all(
        name in result.output
        for name in (
            "doctor",
            "setup",
            "maintenance",
            "storage",
            "identity",
            "resource",
            "slurm",
            "ssh",
            "container",
        )
    )


def test_dev_doctor_json_reports_leaf_package_availability(monkeypatch):
    dev_module = import_module("scitex_hub._cli.dev")
    report = {
        "schema_version": 1,
        "operation": "dev.doctor",
        "mutating": False,
        "ready": False,
        "checks": [{"name": "scitex-hpc", "ok": False}],
        "packages": {"scitex-hpc": {"installed": False}},
    }
    monkeypatch.setattr(dev_module, "collect_dev_doctor", lambda: report)

    result = CliRunner().invoke(main, ["dev", "doctor", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output) == report


def test_root_json_flag_propagates_to_dev_leaf(monkeypatch):
    dev_module = import_module("scitex_hub._cli.dev")
    report = {
        "schema_version": 1,
        "operation": "dev.doctor",
        "mutating": False,
        "ready": True,
        "checks": [],
        "packages": {},
    }
    monkeypatch.setattr(dev_module, "collect_dev_doctor", lambda: report)

    result = CliRunner().invoke(main, ["--json", "dev", "doctor"])

    assert result.exit_code == 0
    assert json.loads(result.output) == report


def test_setup_plan_is_read_only_and_names_ordered_domains():
    result = CliRunner().invoke(main, ["dev", "setup", "plan", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["operation"] == "dev.setup.plan"
    assert payload["mutating"] is False
    assert payload["stages"] == [
        "doctor",
        "storage",
        "identity",
        "resource",
        "ssh",
        "slurm",
        "container",
        "canary",
    ]


def test_maintenance_lists_owner_package_entry_points():
    result = CliRunner().invoke(main, ["dev", "maintenance", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["operation"] == "dev.maintenance.list"
    assert payload["mutating"] is False
    assert payload["owners"]["backup_restore"] == "scitex-storage"
    assert payload["owners"]["runtime_images"] == "scitex-container"


def test_storage_help_lists_audit_validate_and_canary():
    result = CliRunner().invoke(main, ["dev", "storage", "--help"])

    assert result.exit_code == 0
    assert all(name in result.output for name in ("audit", "validate", "canary"))


def test_canary_plan_is_non_mutating_and_contains_no_shell_command():
    result = CliRunner().invoke(
        main,
        ["dev", "storage", "canary", "plan", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["operation"] == "dev.storage.canary.plan"
    assert payload["mutating"] is False
    assert payload["ready"] is False
    assert payload["blockers"] == [
        "typed_storage_runtime_validation",
        "rollback_path",
    ]
    assert payload["target"]["node"] == "scitex-compute-01"
    assert payload["target"]["mountpoint"] == "/scitex-hub"
    assert "command" not in json.dumps(payload).lower()
    assert "argv" not in json.dumps(payload).lower()


def test_domain_groups_expose_validate():
    runner = CliRunner()

    for group in ("identity", "resource", "slurm", "ssh", "container"):
        result = runner.invoke(main, ["dev", group, "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output


def test_storage_audit_delegates_to_owner_package(monkeypatch):
    dev_module = import_module("scitex_hub._cli.dev")
    report = {
        "schema_version": 1,
        "operation": "dev.storage.audit",
        "mutating": False,
        "ready": False,
        "delegate": "scitex-storage",
        "checks": [{"name": "storage_contract_api", "ok": False}],
    }
    monkeypatch.setattr(
        dev_module,
        "collect_leaf_capability",
        lambda distribution: report,
    )

    result = CliRunner().invoke(main, ["dev", "storage", "audit", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == report


def test_storage_validate_exits_nonzero_when_leaf_capability_is_not_ready(monkeypatch):
    dev_module = import_module("scitex_hub._cli.dev")
    monkeypatch.setattr(
        dev_module,
        "collect_leaf_capability",
        lambda distribution: {
            "schema_version": 1,
            "operation": "dev.storage.validate",
            "mutating": False,
            "ready": False,
            "delegate": distribution,
            "checks": [{"name": "storage_contract_api", "ok": False}],
        },
    )

    result = CliRunner().invoke(main, ["dev", "storage", "validate", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["operation"] == "dev.storage.validate"
    assert payload["ready"] is False


def test_identity_report_rejects_subid_errors_and_uid_gid_collisions():
    identity_module = import_module("scitex_hub._cli._dev_identity")

    report = identity_module.build_identity_report(
        passwd_users={"root": 0, "intruder": 20_001},
        groups={"root": 0, "intruder": 20_002},
        expected_users={"alice": 20_001},
        expected_groups={"alice": 20_001},
        authority_errors=[],
        subuid_ranges=[(100000, 65536)],
        subgid_ranges=[(100000, 65536)],
        subuid_errors=["line 2: non-positive count"],
        subgid_errors=[],
        uid_min=20_000,
        uid_max=59_999,
    )

    checks = {item["name"]: item for item in report["checks"]}
    assert report["ready"] is False
    assert checks["uid_collisions"]["ok"] is False
    assert checks["gid_collisions"]["ok"] is False
    assert checks["subuid_source"]["ok"] is False


def test_subid_parser_rejects_empty_owner_and_uid_domain_overflow(tmp_path):
    identity_module = import_module("scitex_hub._cli._dev_identity")
    source = tmp_path / "subuid"
    source.write_text(":100000:65536\nalice:4294967290:10\n", encoding="utf-8")

    ranges, errors = identity_module._read_subid_ranges(source)

    assert ranges == []
    assert len(errors) == 2


def test_identity_report_rejects_authoritative_ids_outside_managed_range():
    identity_module = import_module("scitex_hub._cli._dev_identity")

    report = identity_module.build_identity_report(
        passwd_users={"alice": 1000},
        groups={"alice": 1000},
        expected_users={"alice": 1000},
        expected_groups={"alice": 1000},
        authority_errors=[],
        subuid_ranges=[(100000, 65536)],
        subgid_ranges=[(100000, 65536)],
        subuid_errors=[],
        subgid_errors=[],
        uid_min=20_000,
        uid_max=59_999,
    )

    checks = {item["name"]: item for item in report["checks"]}
    assert report["ready"] is False
    assert checks["expected_uid_range"]["ok"] is False
    assert checks["expected_gid_range"]["ok"] is False


def test_dependency_readiness_requires_distribution_import_and_owned_entrypoint():
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")

    report = dependency_module.build_dependency_report(
        distribution="scitex-ssh",
        module="scitex_ssh",
        executable="scitex-ssh",
        capability="probe_remote",
        domain="ssh",
        version="1.2.0",
        package_owners=["scitex-ssh"],
        module_file_owned=True,
        console_entrypoint_value="scitex_ssh.cli:main",
        capability_entrypoint_value="scitex_ssh:probe_remote",
        runtime_validation={"ready": True},
    )
    wrong_entrypoint = dependency_module.build_dependency_report(
        distribution="scitex-ssh",
        module="scitex_ssh",
        executable="scitex-ssh",
        capability="probe_remote",
        domain="ssh",
        version="1.2.0",
        package_owners=["scitex-ssh"],
        module_file_owned=True,
        console_entrypoint_value="scitex_ssh.not-an-entrypoint",
        capability_entrypoint_value="scitex_ssh:probe_remote",
        runtime_validation={"ready": True},
    )
    ambiguous_owner = dependency_module.build_dependency_report(
        distribution="scitex-ssh",
        module="scitex_ssh",
        executable="scitex-ssh",
        capability="probe_remote",
        domain="ssh",
        version="1.2.0",
        package_owners=["attacker-dist", "scitex-ssh"],
        module_file_owned=True,
        console_entrypoint_value="scitex_ssh.cli:main",
        capability_entrypoint_value="scitex_ssh:probe_remote",
        runtime_validation={"ready": True},
    )
    malformed_module = dependency_module.build_dependency_report(
        distribution="scitex-ssh",
        module="scitex_ssh",
        executable="scitex-ssh",
        capability="probe_remote",
        domain="ssh",
        version="1.2.0",
        package_owners=["scitex-ssh"],
        module_file_owned=True,
        console_entrypoint_value="scitex_ssh.bad-name:main",
        capability_entrypoint_value="scitex_ssh:probe_remote",
        runtime_validation={"ready": True},
    )

    assert report["ready"] is True
    assert wrong_entrypoint["ready"] is False
    assert ambiguous_owner["ready"] is False
    assert malformed_module["ready"] is False


def test_console_entrypoint_rejects_malformed_callable_segments():
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")

    malformed = (
        "scitex_ssh.cli:bad-name",
        "scitex_ssh.cli:bad name",
        "scitex_ssh.cli:.main",
        "scitex_ssh.cli:main.",
        "scitex_ssh.cli:",
    )

    assert all(
        not dependency_module._valid_console_entrypoint(value, "scitex_ssh")
        for value in malformed
    )


def test_duplicate_metadata_owner_rows_are_one_unambiguous_owner():
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")

    report = dependency_module.build_dependency_report(
        distribution="scitex-hpc",
        module="scitex_hpc",
        executable="scitex-hpc",
        capability="validate_customer_policy",
        domain="slurm",
        version="0.9.0",
        package_owners=["scitex-hpc", "scitex-hpc"],
        module_file_owned=True,
        console_entrypoint_value="scitex_hpc._cli:main",
        capability_entrypoint_value="scitex_hpc:validate_customer_policy",
        runtime_validation={"ready": True},
    )

    assert report["ready"] is True


def test_editable_distribution_proves_module_from_direct_url(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "scitex-storage"\n', encoding="utf-8"
    )
    site = tmp_path / "site-packages"
    site.mkdir()
    pth = site / "_editable_scitex_storage.pth"
    pth.write_text(f"{root / 'src'}\n", encoding="utf-8")

    class EditableDistribution:
        files = (Path(pth.name),)
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": root.as_uri(), "dir_info": {"editable": True}}
                )
            return None

        @staticmethod
        def locate_file(name):
            return site / str(name)

    assert dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_rejects_mismatched_project_owner(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "attacker"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "attacker-dist"\n', encoding="utf-8"
    )

    class EditableDistribution:
        files = ()
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": root.as_uri(), "dir_info": {"editable": True}}
                )
            return None

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_requires_declared_pth_mapping(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "scitex-storage"\n', encoding="utf-8"
    )

    class EditableDistribution:
        files = ()
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": root.as_uri(), "dir_info": {"editable": True}}
                )
            return None

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_does_not_double_decode_file_url(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    claimed = tmp_path / "editable%2Froot"
    confused = tmp_path / "editable" / "root"
    claimed.mkdir()
    package = confused / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    for root in (claimed, confused):
        (root / "pyproject.toml").write_text(
            '[project]\nname = "scitex-storage"\n', encoding="utf-8"
        )
    site = tmp_path / "site-packages"
    site.mkdir()
    pth = site / "_editable_scitex_storage.pth"
    pth.write_text(f"{confused / 'src'}\n", encoding="utf-8")

    class EditableDistribution:
        files = (Path(pth.name),)
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": claimed.as_uri(), "dir_info": {"editable": True}}
                )
            return None

        @staticmethod
        def locate_file(name):
            return site / str(name)

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_malformed_metadata_fails_closed(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    root.mkdir()

    class EditableDistribution:
        files = ()
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps({"url": root.as_uri(), "dir_info": None})
            return None

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


@pytest.mark.parametrize("url", ("file:.", "file:"))
def test_editable_distribution_rejects_relative_file_url(
    tmp_path, monkeypatch, url
):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "scitex-storage"\n', encoding="utf-8"
    )
    site = tmp_path / "site-packages"
    site.mkdir()
    pth = site / "_editable_scitex_storage.pth"
    pth.write_text(f"{root / 'src'}\n", encoding="utf-8")
    monkeypatch.chdir(root)

    class EditableDistribution:
        files = (Path(pth.name),)
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps({"url": url, "dir_info": {"editable": True}})
            return None

        @staticmethod
        def locate_file(name):
            return site / str(name)

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_rejects_nested_pth(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "scitex-storage"\n', encoding="utf-8"
    )
    site = tmp_path / "site-packages"
    nested = site / "nested"
    nested.mkdir(parents=True)
    pth = nested / "fake.pth"
    pth.write_text(f"{root / 'src'}\n", encoding="utf-8")

    class EditableDistribution:
        files = (Path("nested/fake.pth"),)
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": root.as_uri(), "dir_info": {"editable": True}}
                )
            return None

        @staticmethod
        def locate_file(name):
            return site / str(name)

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_rejects_tab_import_pth_line(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "scitex-storage"\n', encoding="utf-8"
    )
    site = tmp_path / "site-packages"
    site.mkdir()
    fake_mapping = site / "import\tbenign_target"
    fake_mapping.symlink_to(root / "src", target_is_directory=True)
    pth = site / "_editable_scitex_storage.pth"
    pth.write_text("import\tbenign_target\n", encoding="utf-8")

    class EditableDistribution:
        files = (Path(pth.name),)
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": root.as_uri(), "dir_info": {"editable": True}}
                )
            return None

        @staticmethod
        def locate_file(name):
            return site / str(name)

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_editable_distribution_preserves_leading_pth_whitespace(tmp_path):
    dependency_module = import_module("scitex_hub._cli._dev_dependencies")
    root = tmp_path / "scitex-storage"
    package = root / "src" / "scitex_storage"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "scitex-storage"\n', encoding="utf-8"
    )
    site = tmp_path / "site-packages"
    site.mkdir()
    pth = site / "_editable_scitex_storage.pth"
    pth.write_text(f" {root / 'src'}\n", encoding="utf-8")

    class EditableDistribution:
        files = (Path(pth.name),)
        metadata = {"Name": "scitex-storage"}

        @staticmethod
        def read_text(name):
            if name == "direct_url.json":
                return json.dumps(
                    {"url": root.as_uri(), "dir_info": {"editable": True}}
                )
            return None

        @staticmethod
        def locate_file(name):
            return site / str(name)

    assert not dependency_module._module_file_owned(
        EditableDistribution(), "scitex_storage"
    )


def test_all_check_collections_use_list_schema(monkeypatch):
    dev_module = import_module("scitex_hub._cli.dev")
    monkeypatch.setattr(
        dev_module,
        "collect_identity_report",
        lambda: {
            "schema_version": 1,
            "operation": "dev.identity.validate",
            "mutating": False,
            "ready": True,
            "checks": [],
        },
    )

    result = CliRunner().invoke(main, ["dev", "identity", "validate", "--json"])

    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert isinstance(payload["checks"], list)
    assert payload["operation"].startswith("dev.")
