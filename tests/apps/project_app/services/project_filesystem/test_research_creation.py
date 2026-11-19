"""A new Full project receives its scaffold without losing its Gitea origin."""

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "acceptance-research"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Acceptance")
    git(root, "config", "user.email", "acceptance@example.invalid")
    git(root, "remote", "add", "origin", "https://example.invalid/research.git")
    (root / "README.md").write_text("Gitea initial README\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "Initial commit")
    return root


def populate(target):
    target.mkdir()
    (target / "README.md").write_text("Research showcase\n")
    scripts = target / "scripts" / "mnist"
    scripts.mkdir(parents=True)
    (scripts / "01_fetch_mnist.py").write_text("# research scaffold\n")
    (target / "pipeline.py").symlink_to("scripts/mnist/01_fetch_mnist.py")
    manifest = target / ".scitex" / "template" / "MANIFEST.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("template:\n  id: research\n")
    return True


@pytest.mark.guards(
    defect="Gitea cloned before Full template creation, which skipped existing paths"
)
def test_new_project_gets_research_scaffold(repository, monkeypatch):
    import scitex_template

    from apps.infra.project_app.services.project_filesystem.template_ops import (
        TemplateOperationsManager,
    )

    observed = []

    def clone(**kwargs):
        observed.append(kwargs)
        return populate(Path(kwargs["project_dir"]))

    monkeypatch.setattr(scitex_template, "clone_template", clone)
    manager = TemplateOperationsManager(None)
    manager._customize_after_clone = Mock()
    project = SimpleNamespace(_research_template_pending=True)
    initial_commit = git(repository, "rev-parse", "HEAD")

    assert manager.copy_from_example_template(repository, project, "research")
    assert observed[0]["template_id"] == "research"
    assert (repository / "scripts/mnist/01_fetch_mnist.py").is_file()
    assert (repository / ".scitex/template/MANIFEST.yaml").is_file()
    assert (repository / "pipeline.py").is_symlink()
    assert git(repository, "rev-parse", "HEAD") == initial_commit
    assert git(repository, "remote", "get-url", "origin") == (
        "https://example.invalid/research.git"
    )


@pytest.mark.parametrize("existing", ["authored.py", "scripts/analysis.py"])
def test_refuses_existing_research_contents(repository, existing):
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    authored = repository / existing
    authored.parent.mkdir(exist_ok=True)
    authored.write_text("authored research\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Research")
    callback = Mock(side_effect=populate)

    assert not populate_new_repository(repository, callback)
    callback.assert_not_called()
    assert authored.read_text() == "authored research\n"


def test_refuses_modified_initial_readme(repository):
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    (repository / "README.md").write_text("Authored text\n")
    callback = Mock(side_effect=populate)

    assert not populate_new_repository(repository, callback)
    callback.assert_not_called()
    assert (repository / "README.md").read_text() == "Authored text\n"


def test_failed_fetch_preserves_initial_repository(repository):
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    before = (repository / "README.md").read_bytes()

    def fail(target):
        populate(target)
        return False

    assert not populate_new_repository(repository, fail)
    assert (repository / "README.md").read_bytes() == before
    assert git(repository, "status", "--porcelain") == ""


def test_existing_project_cannot_request_overlay(repository):
    from apps.infra.project_app.services.project_filesystem.template_ops import (
        TemplateOperationsManager,
    )

    assert not TemplateOperationsManager(None).copy_from_example_template(
        repository, SimpleNamespace(), "research"
    )


def test_failed_template_does_not_report_empty_project_as_success(tmp_path):
    from apps.infra.project_app.services.project_filesystem.manager import (
        ProjectOpsManager,
    )

    manager = object.__new__(ProjectOpsManager)
    manager._get_effective_base_path = Mock(return_value=tmp_path)
    manager._ensure_directory = Mock(return_value=True)
    manager.template_ops = Mock()
    manager.template_ops.copy_from_example_template.return_value = False
    project = SimpleNamespace(slug="acceptance-research", save=Mock())

    assert manager.create_project_directory(project, use_template=True) == (False, None)
    manager.template_ops.create_minimal_readme.assert_not_called()
    project.save.assert_not_called()
