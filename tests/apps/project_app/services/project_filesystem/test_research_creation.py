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
    # Arrange
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

    # Act
    success = manager.copy_from_example_template(repository, project, "research")
    # Assert
    assert (
        success,
        observed[0]["template_id"] if observed else None,
        (repository / "scripts/mnist/01_fetch_mnist.py").is_file(),
        (repository / ".scitex/template/MANIFEST.yaml").is_file(),
        (repository / "pipeline.py").is_symlink(),
        git(repository, "rev-parse", "HEAD"),
        git(repository, "remote", "get-url", "origin"),
    ) == (
        True,
        "research",
        True,
        True,
        True,
        initial_commit,
        "https://example.invalid/research.git",
    )


@pytest.mark.parametrize("existing", ["authored.py", "scripts/analysis.py"])
def test_refuses_existing_research_contents(repository, existing):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    authored = repository / existing
    authored.parent.mkdir(exist_ok=True)
    authored.write_text("authored research\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Research")
    callback = Mock(side_effect=populate)

    # Act
    success = populate_new_repository(repository, callback)
    # Assert
    assert (success, callback.call_count, authored.read_text()) == (
        False,
        0,
        "authored research\n",
    )


def test_refuses_modified_initial_readme(repository):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    (repository / "README.md").write_text("Authored text\n")
    callback = Mock(side_effect=populate)

    # Act
    success = populate_new_repository(repository, callback)
    # Assert
    assert (success, callback.call_count, (repository / "README.md").read_text()) == (
        False,
        0,
        "Authored text\n",
    )


def test_failed_fetch_preserves_initial_repository(repository):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    before = (repository / "README.md").read_bytes()

    def fail(target):
        populate(target)
        return False

    # Act
    success = populate_new_repository(repository, fail)
    # Assert
    assert (
        success,
        (repository / "README.md").read_bytes(),
        git(repository, "status", "--porcelain"),
    ) == (False, before, "")


def test_existing_project_cannot_request_overlay(repository):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.template_ops import (
        TemplateOperationsManager,
    )

    manager = TemplateOperationsManager(None)
    # Act
    success = manager.copy_from_example_template(
        repository, SimpleNamespace(), "research"
    )
    # Assert
    assert not success


def test_failed_template_does_not_report_empty_project_as_success(tmp_path):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.manager import (
        ProjectOpsManager,
    )

    manager = object.__new__(ProjectOpsManager)
    manager._get_effective_base_path = Mock(return_value=tmp_path)
    manager._ensure_directory = Mock(return_value=True)
    manager.template_ops = Mock()
    manager.template_ops.copy_from_example_template.return_value = False
    project = SimpleNamespace(slug="acceptance-research", save=Mock())

    # Act
    result = manager.create_project_directory(project, use_template=True)
    # Assert
    assert (
        result,
        manager.template_ops.create_minimal_readme.call_count,
        project.save.call_count,
    ) == ((False, None), 0, 0)
