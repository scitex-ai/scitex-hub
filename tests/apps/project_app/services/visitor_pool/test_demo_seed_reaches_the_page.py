#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A new visitor's project must render as a WORKED EXAMPLE, not as a skeleton.

WHAT WENT WRONG (prod, measured 2026-08-16)
-------------------------------------------
The demo pages did not error. They were EMPTY. Rendered as a real anonymous
visitor, ``/apps/writer/`` showed the scitex-writer template's own stubs
verbatim --- "Replace this text with your manuscript abstract.", "Replace this
with your introduction." --- over a 29-word manuscript with NO TITLE at all
(``section/title/`` returned ``content: ""``). The project browser listed no
README, no data, and not one image. The operator was taking grant-application
screenshots of this.

WHY THE EXISTING CHECK COULD NOT HAVE CAUGHT IT
-----------------------------------------------
``template_clone.verify_template_marker`` passes when ``.scitex/writer/``
exists and is non-empty --- which every one of those empty-looking projects
did. A marker is a statement about the DISK. Emptiness is a statement about the
PAGE. Writing another disk-shaped assertion here would rebuild the exact blind
spot, so this module asserts through the HTTP endpoint the Writer editor itself
calls (``GET /apps/writer/api/project/<id>/section/<name>/``, i.e.
``writer_app:api_section``), driven by the REAL reset pipeline end to end.

WHAT "RED" LOOKED LIKE BEFORE THE FIX
-------------------------------------
With ``demo_seed`` written but its call in
``workspace_manager._initialize_reset_directory`` not yet wired, this suite
reported ``27 failed, 4 passed``, and the page handed back the template stub
verbatim::

    E   AssertionError: manuscript/abstract still renders the template stub:
        '\\begin{abstract}\\n\\nReplace this text with your manuscript
        abstract. Typically 150--250 words summarizing objectives, methods,
        key findings, and conclusions.\\n\\n\\end{abstract}\\n'
    E   AssertionError: manuscript/introduction still renders the template
        stub: '\\section{Introduction}\\n\\nReplace this with your
        introduction.\\n'
    E   AssertionError: manuscript/results still renders the template stub:
        '\\section{Results}\\n\\nReplace this with your results.\\n'

The 4 that passed are the anti-vacuity check and three name assertions —
neither of which depends on seeding, which is exactly why they are not the
guard.

THE FAKE CLONE IS THE REAL TEMPLATE'S TEXT
------------------------------------------
``fake_clone`` below writes the placeholder strings MEASURED VERBATIM from a
real ``scitex_minimal`` clone (scitex-template 0.7.0 / scitex-writer 2.41.0) at
the real paths. That is what makes the red honest: the test fails against
exactly what production shipped, not against an empty string that any code
change would accidentally satisfy. No network, no mocks --- a tiny real
directory tree injected through the production ``clone_fn`` seam.

Run (SQLite, no network/Gitea):

    SCITEX_HUB_USE_SQLITE_DEV=1 \
    /opt/venv-sac/bin/python -m pytest <abs path to this file>
"""

import json
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.visitor_pool.demo_seed import (
    SENTINEL_RELPATHS,
    demo_content_is_present,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
    WorkspaceManager,
)

SLUG = WorkspaceManager.DEFAULT_PROJECT_SLUG

# Measured verbatim from a real scitex_minimal clone. If the upstream template
# ever stops shipping these, this suite's fake goes stale rather than wrong --
# the page assertions below are on the DEMO text, and the stub assertions are
# their negative siblings.
STUB_ABSTRACT = (
    "Replace this text with your manuscript abstract. Typically 150--250 "
    "words summarizing objectives, methods, key findings, and conclusions."
)
STUB_INTRODUCTION = "Replace this with your introduction."
STUB_TITLE = "Your Manuscript Title Here"
STUB_MARKER = "Replace this"

# One phrase per section that ONLY the seeded demo can produce. Deliberately
# specific: "non-empty" alone would pass on the stub text, which is also
# non-empty -- that is precisely how this defect survived.
DEMO_PHRASES = {
    "manuscript/abstract": "worked example distributed with SciTeX",
    "manuscript/introduction": "This is an example, not a study",
    # Not the bare filename: the manuscript spells it \texttt{digits\_sample
    # .csv}, LaTeX-escaped, so an unescaped needle never matches.
    "manuscript/methods": "stratified random subset of 500",
    "manuscript/results": "131 of the 150 held-out images",
    # Needles must not span a source line break -- the .tex is hard-wrapped,
    # so "linearly separable" is stored as "linearly\nseparable".
    "manuscript/discussion": "separable in raw pixel space",
}


# ---------------------------------------------------------------------------
# Tiny real fakes (no unittest.mock) injected through the production seams
# ---------------------------------------------------------------------------


class FakeGiteaClient:
    """In-memory Gitea: the visitor owns no repos; deletion is a no-op."""

    def list_repositories(self, username):
        return []

    def delete_repository(self, owner, repo):
        return True


def fake_clone(template_id, dest, git_strategy=None):
    """A faithful ``scitex_minimal``: the real layout, the real stub text.

    ``02_supplementary`` and ``03_revision`` are not decoration --
    ``scitex_writer.Writer._validate_structure`` (writer.py:194-205) refuses
    to attach without all three document roots, and the Writer HTTP endpoint
    this suite reads through returns 500 when it does. A fake missing them
    fails for the wrong reason and proves nothing about the seed.
    """
    writer = Path(dest) / TEMPLATE_MARKER_RELPATH
    shared = writer / "00_shared"
    contents = writer / "01_manuscript" / "contents"
    media = contents / "figures" / "caption_and_media" / "jpg_for_compilation"
    for directory in (shared, contents, media):
        directory.mkdir(parents=True, exist_ok=True)
    for sibling in ("02_supplementary", "03_revision"):
        (writer / sibling / "contents").mkdir(parents=True, exist_ok=True)

    (shared / "title.tex").write_text(
        "\\newcommand{\\scitexmanuscripttitle}{%\n"
        f"{STUB_TITLE}\n"
        "}\n\\title{\\scitexmanuscripttitle}\n"
    )
    (shared / "authors.tex").write_text(
        "\\author[1]{First Author}\n\\author[2]{Second Author}\n"
    )
    (shared / "keywords.tex").write_text(
        "\\begin{keyword}\nkeyword one \\sep keyword two\n\\end{keyword}\n"
    )
    (contents / "abstract.tex").write_text(
        f"\\begin{{abstract}}\n\n{STUB_ABSTRACT}\n\n\\end{{abstract}}\n"
    )
    (contents / "introduction.tex").write_text(
        f"\\section{{Introduction}}\n\n{STUB_INTRODUCTION}\n"
    )
    for name in ("methods", "results", "discussion"):
        (contents / f"{name}.tex").write_text(
            f"\\section{{{name.capitalize()}}}\n\nReplace this with your {name}.\n"
        )
    captions = contents / "figures" / "caption_and_media"
    for stub in ("01_example_figure", "02_another_example"):
        (captions / f"{stub}.tex").write_text(
            "\\caption{\\textbf{Replace with your figure title.}}\n"
            f"\\label{{fig:{stub}}}\n"
        )
    (media / ".gitkeep").write_text("")
    (writer / "compile.sh").write_text("#!/bin/bash\n")
    return True


def no_container_toolchain(argv, timeout=None):
    """``run_cmd`` seam: a host with no SLURM/apptainer binaries."""
    raise FileNotFoundError(argv[0])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def visitor(db):
    """A pool visitor whose workspace lives under this test's tmp root."""
    username = "visitor-001"
    return User.objects.create(username=username, email=f"{username}@visitor.local")


@pytest.fixture
def seeded_project(visitor):
    """Drive the REAL reset pipeline; return the row it created."""
    WorkspaceManager.reset_visitor_workspace(
        visitor,
        gitea_client=FakeGiteaClient(),
        clone_fn=fake_clone,
        run_cmd=no_container_toolchain,
    )
    return Project.objects.get(owner=visitor, slug=SLUG)


@pytest.fixture
def project_path(seeded_project):
    """Where that pipeline put the workspace on disk."""
    return Path(seeded_project.git_clone_path)


@pytest.fixture
def visitor_client(visitor):
    """A logged-in visitor -- the audience the screenshots are of."""
    client = Client()
    client.force_login(visitor)
    return client


def read_section(client, project, section_id):
    """GET one section through the endpoint the Writer editor calls."""
    url = reverse("writer_app:api_section", args=[project.id, section_id])
    response = client.get(url)
    assert response.status_code == 200, (
        f"{section_id}: endpoint returned {response.status_code}, so nothing "
        f"about the page can be asserted"
    )
    payload = json.loads(response.content)
    assert payload.get("success") is True, f"{section_id}: {payload}"
    return payload


# ---------------------------------------------------------------------------
# THE GUARD: the seed reaches the PAGE, not merely the disk
# ---------------------------------------------------------------------------


class TestWriterRendersTheDemoManuscript:
    """``GET writer_app:api_section`` -- the editor's own read path."""

    @pytest.mark.parametrize("section_id", sorted(DEMO_PHRASES))
    def test_section_is_not_the_template_stub(
        self, visitor_client, seeded_project, section_id
    ):
        """THE DEFECT: every section rendered "Replace this…" in production."""
        # Arrange
        payload = read_section(visitor_client, seeded_project, section_id)
        # Act
        actual = payload["content"]
        # Assert
        assert STUB_MARKER not in actual, (
            f"{section_id} still renders the template stub: {actual!r}"
        )

    @pytest.mark.parametrize("section_id", sorted(DEMO_PHRASES))
    def test_section_renders_the_demo_text(
        self, visitor_client, seeded_project, section_id
    ):
        """Positive sibling: the DEMO's own words came back, not just "not
        the stub". A blank file would pass the negative test above."""
        # Arrange
        payload = read_section(visitor_client, seeded_project, section_id)
        phrase = DEMO_PHRASES[section_id]
        # Act
        actual = payload["content"]
        # Assert
        assert phrase in actual, (
            f"{section_id} does not contain {phrase!r}; got {actual[:400]!r}"
        )

    @pytest.mark.parametrize("section_id", sorted(DEMO_PHRASES))
    def test_section_is_substantial(self, visitor_client, seeded_project, section_id):
        """The whole manuscript measured 29 words. A section that renders a
        single line is still an empty page in a screenshot."""
        # Arrange
        payload = read_section(visitor_client, seeded_project, section_id)
        # Act
        actual = len(payload["content"].split())
        # Assert
        assert actual >= 80, f"{section_id} rendered only {actual} words"

    def test_manuscript_has_a_title(self, visitor_client, seeded_project):
        """``section/title/`` returned ``content: ""`` in production -- the
        manuscript had no title at all."""
        # Arrange
        payload = read_section(visitor_client, seeded_project, "shared/title")
        # Act
        actual = payload["content"]
        # Assert
        assert "Classifying Handwritten Digits" in actual, (
            f"shared/title rendered {actual!r}"
        )

    def test_title_is_not_the_template_placeholder(
        self, visitor_client, seeded_project
    ):
        """Negative sibling for the title."""
        # Arrange
        payload = read_section(visitor_client, seeded_project, "shared/title")
        # Act
        actual = payload["content"]
        # Assert
        assert STUB_TITLE not in actual

    def test_the_stub_is_what_an_unseeded_project_would_have_rendered(self):
        """ANTI-VACUITY: prove the fake really carries the defect's text.

        Without this, a future edit that quietly emptied ``fake_clone`` would
        turn every negative assertion above green by removing the thing they
        assert the absence of.
        """
        # Arrange
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            fake_clone("scitex_minimal", tmp)
            stub_file = (
                Path(tmp)
                / TEMPLATE_MARKER_RELPATH
                / "01_manuscript"
                / "contents"
                / "abstract.tex"
            )
            # Act
            actual = stub_file.read_text()
        # Assert
        assert STUB_MARKER in actual


# ---------------------------------------------------------------------------
# The rest of the project: what the file browser photographs
# ---------------------------------------------------------------------------


class TestProjectRootCarriesTheDemoProject:
    """The project page listed six dotfiles and no content of any kind."""

    @pytest.mark.parametrize("relpath", SENTINEL_RELPATHS)
    def test_sentinel_file_exists(self, project_path, relpath):
        """README, dataset, script, and both figures reach the workspace."""
        # Arrange
        target = project_path / relpath
        # Act
        actual = target.is_file()
        # Assert
        assert actual, f"{relpath} missing under {project_path}"

    def test_dataset_is_not_empty(self, project_path):
        """A zero-byte CSV would satisfy the existence check above."""
        # Arrange
        csv_path = project_path / "data" / "digits_sample.csv"
        # Act
        actual = len(csv_path.read_text().splitlines())
        # Assert
        assert actual == 501, f"expected 500 rows + header, got {actual}"

    def test_figures_are_real_images(self, project_path):
        """PNG magic bytes -- an empty placeholder file would not have them."""
        # Arrange
        figures = sorted((project_path / "figures").glob("*.png"))
        # Act
        actual = [f.read_bytes()[:8] for f in figures]
        # Assert
        assert actual and all(head == b"\x89PNG\r\n\x1a\n" for head in actual), (
            f"figures/ holds {[f.name for f in figures]}"
        )

    def test_manuscript_carries_a_compilable_figure(self, project_path):
        """The template shipped ONLY a .gitkeep here -- no image existed
        anywhere in the tree, so no compile could ever show one."""
        # Arrange
        media = (
            project_path
            / TEMPLATE_MARKER_RELPATH
            / "01_manuscript"
            / "contents"
            / "figures"
            / "caption_and_media"
            / "jpg_for_compilation"
        )
        # Act
        actual = sorted(p.name for p in media.glob("*.jpg"))
        # Assert
        assert actual == ["01_digit_grid.jpg", "02_confusion_matrix.jpg"]

    def test_placeholder_captions_are_gone(self, project_path):
        """ "Replace with your figure title." must not survive beside the
        demo's own two captions."""
        # Arrange
        captions = (
            project_path
            / TEMPLATE_MARKER_RELPATH
            / "01_manuscript"
            / "contents"
            / "figures"
            / "caption_and_media"
        )
        # Act
        actual = sorted(p.name for p in captions.glob("*.tex"))
        # Assert
        assert actual == ["01_digit_grid.tex", "02_confusion_matrix.tex"]

    def test_helper_agrees_the_content_landed(self, project_path):
        """``demo_content_is_present`` is the operator-facing shorthand."""
        # Arrange
        path = project_path
        # Act
        actual = demo_content_is_present(path)
        # Assert
        assert actual


# ---------------------------------------------------------------------------
# The name a stranger reads
# ---------------------------------------------------------------------------


class TestProjectIsNamedForAStranger:
    """ "My Project" said nothing about what the project contains."""

    def test_display_name_names_the_example(self, seeded_project):
        """Positive: the switcher reads as an example project."""
        # Arrange
        project = seeded_project
        # Act
        actual = project.name
        # Assert
        assert actual == "Handwritten Digits (Example)"

    def test_display_name_is_not_the_slug(self, seeded_project):
        """The older defect, still guarded."""
        # Arrange
        project = seeded_project
        # Act
        actual = project.name
        # Assert
        assert actual != project.slug

    def test_slug_is_still_the_load_bearing_literal(self, seeded_project):
        """Renaming the NAME must never move the SLUG."""
        # Arrange
        project = seeded_project
        # Act
        actual = project.slug
        # Assert
        assert actual == "default-project"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
