"""A template scaffold lands only in an untouched new Gitea clone.

The full path -- every /new/ tab against a real Gitea and the real template
packages -- is tests/apps/project_app/views/projects/test_create.py. These
pin the guards of the overlay step itself, without a server.
"""

import subprocess
from pathlib import Path
from types import SimpleNamespace

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


class Scaffold:
    """A template stand-in that writes a small research tree and counts calls."""

    def __init__(self, result=True):
        self.result = result
        self.targets = []

    def __call__(self, target):
        self.targets.append(target)
        target = Path(target)
        target.mkdir()
        (target / "README.md").write_text("Research showcase\n")
        scripts = target / "scripts" / "mnist"
        scripts.mkdir(parents=True)
        (scripts / "01_fetch_mnist.py").write_text("# research scaffold\n")
        (target / "pipeline.py").symlink_to("scripts/mnist/01_fetch_mnist.py")
        return self.result


def test_scaffold_overlays_new_clone_and_keeps_its_identity(repository):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.new_repository_template import (
        populate_new_repository,
    )

    initial_commit = git(repository, "rev-parse", "HEAD")

    # Act
    success = populate_new_repository(repository, Scaffold())
    # Assert
    assert (
        success,
        (repository / "scripts/mnist/01_fetch_mnist.py").is_file(),
        (repository / "pipeline.py").is_symlink(),
        git(repository, "rev-parse", "HEAD"),
        git(repository, "remote", "get-url", "origin"),
    ) == (
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
    scaffold = Scaffold()

    # Act
    success = populate_new_repository(repository, scaffold)
    # Assert
    assert (success, len(scaffold.targets), authored.read_text()) == (
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
    scaffold = Scaffold()

    # Act
    success = populate_new_repository(repository, scaffold)
    # Assert
    assert (success, len(scaffold.targets), (repository / "README.md").read_text()) == (
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

    # Act
    success = populate_new_repository(repository, Scaffold(result=False))
    # Assert
    assert (
        success,
        (repository / "README.md").read_bytes(),
        git(repository, "status", "--porcelain"),
    ) == (False, before, "")


@pytest.mark.parametrize("template_type", ["minimal", "research"])
def test_existing_project_cannot_request_overlay(repository, template_type):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.template_ops import (
        TemplateOperationsManager,
    )

    manager = TemplateOperationsManager(None)
    # Act
    success = manager.copy_from_example_template(
        repository, SimpleNamespace(), template_type
    )
    # Assert
    assert not success


class RefusingTemplates:
    """Template operations whose scaffold always fails; records README writes."""

    def __init__(self):
        self.readmes = []

    def copy_from_example_template(self, project_path, project, template_type):
        return False

    def create_minimal_readme(self, project, project_path):
        self.readmes.append(project_path)


class UnsavedProject:
    slug = "acceptance-research"
    is_org_owned = False

    def __init__(self):
        self.saves = 0

    def save(self, *args, **kwargs):
        self.saves += 1


def test_failed_template_does_not_report_empty_project_as_success(tmp_path):
    # Arrange
    from apps.infra.project_app.services.project_filesystem.manager import (
        ProjectOpsManager,
    )

    manager = object.__new__(ProjectOpsManager)
    manager.base_path = tmp_path
    manager.template_ops = RefusingTemplates()
    project = UnsavedProject()

    # Act
    result = manager.create_project_directory(project, use_template=True)
    # Assert
    assert (result, manager.template_ops.readmes, project.saves) == (
        (False, None),
        [],
        0,
    )
