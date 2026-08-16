#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lay real demo content on top of a freshly cloned template.

WHY THIS EXISTS
---------------
``scitex_minimal`` is a placeholder SKELETON, not an example. Measured against
scitex-template 0.7.0 / scitex-writer 2.41.0, a clone puts exactly one entry at
the project root (``.scitex/``) and fills the manuscript with its own stubs::

    00_shared/title.tex   \\newcommand{\\scitexmanuscripttitle}{Your Manuscript Title Here}
    contents/abstract.tex "Replace this text with your manuscript abstract."
    contents/introduction.tex "Replace this with your introduction."
    contents/figures/caption_and_media/jpg_for_compilation/  -> only .gitkeep

So a brand-new workspace does not ERROR — it renders EMPTY. Writer shows
"Replace this…" over a 29-word manuscript with no title, the project browser
lists no README and no data, and there is not one image anywhere in the tree.
That is what a first-time visitor sees, and it is what a grant reviewer sees in
a screenshot.

WHY THE FIX LIVES HERE AND NOT IN THE TEMPLATE
----------------------------------------------
Enriching ``scitex_minimal`` itself would change what EVERY new project
everywhere contains, in a package this repo does not own. That is a
conversation, not a patch. This module takes the narrow, reversible route:
hub seeds content ON TOP of the clone, for the visitor/default project only,
after the clone has already passed marker verification. Deleting this module
and its three call sites restores the previous behaviour exactly.

WHY THE MARKER CHECK COULD NOT HAVE CAUGHT THIS
-----------------------------------------------
``template_clone.verify_template_marker`` passes when ``.scitex/writer/`` exists
and is non-empty. Every empty-looking project above satisfies it. A marker is a
statement about the DISK; emptiness is a statement about the PAGE. The guard for
this module is therefore
``tests/apps/project_app/services/visitor_pool/test_demo_seed_reaches_the_page.py``,
which drives the real reset pipeline and then reads the seeded text back out of
the Writer HTTP endpoint the editor itself calls. A marker-style assertion here
would reproduce the exact blind spot this module exists to close.

WHY A SEEDING FAILURE MUST NOT QUARANTINE A SLOT
------------------------------------------------
Everything ``reset_visitor_workspace`` raises becomes ``quarantine_reason`` and
kills the slot (see ``template_clone``'s module docstring). A visitor holding an
UNSEEDED but otherwise working workspace is strictly better off than a visitor
holding a dead slot: the demo content is a shop window, not a dependency. So the
call sites use :func:`try_seed_demo_content`, which logs at ERROR and returns
False. The failure is not silent — it is loud in the log and red in CI, because
the guard above drives the strict path.
"""

import logging
import shutil
from pathlib import Path

from ..writer_workspace_layout import WRITER_WORKSPACE_RELPATH

logger = logging.getLogger(__name__)

# Where the demo content ships. Committed to this repo rather than generated at
# provision time on purpose: seeding must not need sklearn/matplotlib, must not
# need the network, and must produce byte-identical output on every slot.
PAYLOAD_ROOT = Path(__file__).resolve().parent / "demo_seed_payload"

# Copied verbatim onto the PROJECT ROOT: README.md, data/, scripts/, figures/.
PROJECT_PAYLOAD_DIR = PAYLOAD_ROOT / "project"

# Copied onto ``.scitex/writer/``, overwriting the template's own stubs.
WRITER_PAYLOAD_DIR = PAYLOAD_ROOT / "writer"

# The template's two placeholder figure captions ("Replace with your figure
# title."). The demo ships its own two captions under real names, so leaving
# these behind would put four figures in a two-figure manuscript, two of them
# captioned "Replace with…". Removed rather than overwritten so the names in the
# tree match the names in the text.
SUPERSEDED_TEMPLATE_FILES = (
    "01_manuscript/contents/figures/caption_and_media/01_example_figure.tex",
    "01_manuscript/contents/figures/caption_and_media/02_another_example.tex",
)

# Read back by the guard test and by :func:`demo_content_is_present` as the
# cheap on-disk sanity check. NOT a substitute for the page-level assertions —
# see the module docstring.
SENTINEL_RELPATHS = (
    "README.md",
    "data/digits_sample.csv",
    "scripts/reproduce_figures.py",
    "figures/digit_grid.png",
    "figures/confusion_matrix.png",
)


class DemoSeedError(RuntimeError):
    """Seeding the demo content failed. Never fatal to a visitor slot."""


def _copy_tree(source: Path, destination: Path) -> list[Path]:
    """Copy ``source`` over ``destination``, returning the files written.

    Overwrites file-by-file rather than replacing the directory, so seeding a
    project that already carries a template (or an earlier seed) is idempotent
    and never deletes anything the copy does not itself replace.
    """
    written: list[Path] = []
    for item in sorted(source.rglob("*")):
        if item.is_dir():
            continue
        target = destination / item.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        written.append(target)
    return written


def seed_demo_content(project_path) -> list[Path]:
    """Write the demo project's content into ``project_path``.

    Runs AFTER the template clone and its marker verification, so the writer
    workspace it overwrites is known to exist.

    Returns
    -------
    list[Path]
        Absolute paths of every file written, project-root files first.

    Raises
    ------
    DemoSeedError
        If the payload is missing, or if the project has no writer workspace to
        seed into. Callers that must not kill a slot should use
        :func:`try_seed_demo_content` instead.
    """
    project_path = Path(project_path)

    if not PROJECT_PAYLOAD_DIR.is_dir() or not WRITER_PAYLOAD_DIR.is_dir():
        raise DemoSeedError(
            f"demo payload missing at {PAYLOAD_ROOT} — expected 'project/' and "
            f"'writer/' subdirectories. The payload is committed alongside this "
            f"module; a deployment that strips non-Python files from "
            f"apps/infra/project_app/services/visitor_pool/ would cause this."
        )

    writer_dir = project_path / WRITER_WORKSPACE_RELPATH
    if not writer_dir.is_dir():
        raise DemoSeedError(
            f"no writer workspace at {writer_dir} — seed_demo_content must run "
            f"AFTER the template clone and its marker verification"
        )

    written = _copy_tree(PROJECT_PAYLOAD_DIR, project_path)
    written += _copy_tree(WRITER_PAYLOAD_DIR, writer_dir)

    for relpath in SUPERSEDED_TEMPLATE_FILES:
        stub = writer_dir / relpath
        if stub.is_file():
            stub.unlink()

    logger.info(
        f"[VisitorPool] Seeded demo content into {project_path} ({len(written)} files)"
    )
    return written


def try_seed_demo_content(project_path) -> bool:
    """Seed, logging any failure instead of raising.

    Used by the three provisioning call sites: demo content is a shop window,
    not a dependency, and a visitor with an unseeded workspace is better served
    than a visitor with a quarantined slot.
    """
    try:
        seed_demo_content(project_path)
        return True
    except Exception as exc:
        logger.error(
            f"[VisitorPool] Demo content seeding failed for {project_path}: "
            f"{exc}. The workspace is still usable; it will just look empty.",
            exc_info=True,
        )
        return False


def demo_content_is_present(project_path) -> bool:
    """True if every sentinel file the demo ships is on disk.

    A convenience for operators and for anti-vacuity assertions. It says the
    files ARRIVED; it does NOT say the apps render them, which is the failure
    mode that made this module necessary.
    """
    project_path = Path(project_path)
    return all((project_path / relpath).is_file() for relpath in SENTINEL_RELPATHS)


# EOF
