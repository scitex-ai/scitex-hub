"""Synthetic gallery fixtures obey the real Cards admission rules."""

import importlib.util
from pathlib import Path


def test_mnist_showcase_rows_are_valid_non_runnable_and_muted():
    # Arrange -- fixture construction is pure; no store connection is opened.
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "mnist_board_showcase", root / "scripts/showcase/mnist_cards_board.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from scitex_cards._runnable import runnable_tasks
    from scitex_cards._validate import _validate_tasks

    rows = module.fixture_rows("example-human")
    # Act -- exercise the owning package's real validation and work classifier.
    _validate_tasks(rows, source="owned fixture validation", strict=True)
    result = (
        len({r["id"] for r in rows}),
        runnable_tasks(rows).tasks,
        all(
            r["kind"] == "status"
            and r["assignee"] == "example-human"
            and r["notify"] == {"events": {"created": []}, "mute": ["example-human"]}
            and r["title"].startswith("Demo:")
            for r in rows
        ),
    )
    # Assert -- no synthetic card can become queued agent work.
    assert result == (4, [], True)
