#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_dev_preview/test_sync_with_a_real_clone.py

"""One sync tick against a REAL git clone, with recording actions and cards.

Every test builds a bare origin, a preview clone on ``develop`` and a second
writer clone that pushes new commits to origin — all real ``git`` in
``tmp_path``. The two side effects the engine has (shelling out to make /
docker, filing board cards) are replaced by REAL Python callables that record
what they were asked to do; no mock library, per fleet rule. Each test pins
one clause of the sync contract in :mod:`scitex_hub._dev_preview._sync`:

* the first ever run records HEAD as applied and does nothing (it never
  rebuilds the world);
* a ``.py`` commit is fast-forwarded and recorded with no action (autoreload);
* a Dockerfile / ``.ts`` / compose / migration commit triggers EXACTLY
  ``rebuild`` / ``npm_build`` / ``reload`` / ``migrate``;
* tracked dirt refuses the tick and leaves HEAD alone; a diverged clone is
  refused, never force-reset; a refusal files ONE ``operator-decision`` card;
* a rebuild that fails twice HOLDS the head — the third run calls nothing —
  and files exactly one ``dependency`` card; a later successful head resolves it;
* a second sync while the ``flock`` is held reports ``already_running``;
* ``--dry-run`` fetches (so the plan is real) but does not move HEAD, and
  says ``would REFUSE`` when the real tick would;
* every way a tick can die mid-action still counts toward the hold: an
  action raising a foreign exception, and a tick SIGTERMed by
  ``/usr/bin/timeout`` (a real subprocess under the real ``timeout``);
* a clone that is AHEAD of origin (local commit, or origin force-pushed
  backwards) is refused, not treated as a resume or as up to date;
* a non-ASCII TypeScript filename still triggers ``npm_build`` (git quotes
  such paths unless asked for ``-z``);
* a card the board REJECTED is retried next tick; a fetch failure neither
  consumes a rebuild attempt nor leaves its card open once fetch recovers;
  an ``applied_head`` the clone does not have is re-baselined, not failed
  forever; a success prunes attempts of superseded heads.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest

from scitex_hub._dev_preview import ActionFailed, Actions, Config, Outcome, sync
from scitex_hub._dev_preview._lock import LOCK_FILE
from scitex_hub._dev_preview._state import RC_KILLED
from scitex_hub._dev_preview._sync import (
    CARD_CLONE_REFUSED,
    CARD_FETCH_FAILED,
    CARD_SYNC_FAILED,
)

DOCKERFILE = "deployment/docker/docker_dev/Dockerfile"
COMPOSE = "deployment/docker/docker_dev/docker-compose.yml"
WORKTREE_SRC = Path(__file__).resolve().parents[3] / "src"
UNREACHABLE_REMOTE = "/nonexistent/dev-preview-origin.git"

# A tick whose rebuild sleeps far longer than the ``/usr/bin/timeout`` it runs
# under; ``sys.argv``: clone, state_dir. Real signal, real process, real state.
SLOW_TICK_DRIVER = """\
import sys
import time
from pathlib import Path

from scitex_hub._dev_preview import Actions, Config, sync


def slow_rebuild(clone):
    time.sleep(30)
    return 0


class AcceptingCards:
    def file_blocked(self, card_id, title, note, blocker):
        return True

    def resolve(self, card_id, note):
        return True


print(
    sync(
        Config(
            clone=Path(sys.argv[1]),
            state_dir=Path(sys.argv[2]),
            actions=Actions(
                rebuild=slow_rebuild, wait_healthy=lambda c, timeout=600: None
            ),
            cards=AcceptingCards(),
        )
    ).status
)
"""


def _git(cwd: Path, *args: str) -> str:
    """Run ``git -C <cwd> <args>`` and return stripped stdout; raise on failure."""
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.stdout.strip()


def _identify(repo: Path) -> None:
    _git(repo, "config", "user.email", "dev-preview-test@example.com")
    _git(repo, "config", "user.name", "dev-preview test")


@dataclass
class Repos:
    """The three repositories one test works with, plus the engine state dir."""

    origin: Path
    clone: Path
    writer: Path
    state_dir: Path

    def push(self, relpath: str, content: str = "changed\n") -> str:
        """Commit ``relpath`` in the writer clone, push to origin, return the new SHA."""
        target = self.writer / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        _git(self.writer, "add", "--all")
        _git(self.writer, "commit", "--quiet", "-m", f"change {relpath}")
        _git(self.writer, "push", "--quiet", "origin", "develop")
        return _git(self.writer, "rev-parse", "HEAD")

    def head(self) -> str:
        return _git(self.clone, "rev-parse", "HEAD")

    def state(self) -> dict:
        return json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))

    def force_push_back_to(self, sha: str) -> None:
        """Rewrite origin's ``develop`` to ``sha`` (what a backwards force-push does)."""
        _git(self.writer, "reset", "--hard", "--quiet", sha)
        _git(self.writer, "push", "--force", "--quiet", "origin", "develop")

    def break_remote(self) -> str:
        """Point the clone's origin at a path that does not exist; return the old URL."""
        url = _git(self.clone, "remote", "get-url", "origin")
        _git(self.clone, "remote", "set-url", "origin", UNREACHABLE_REMOTE)
        return url

    def restore_remote(self, url: str) -> None:
        _git(self.clone, "remote", "set-url", "origin", url)


class RecordingActions:
    """Real callables that record the engine's calls; nothing shells out.

    ``failing`` names one action that raises :class:`ActionFailed` every
    time, which is how the retry gate is exercised without a broken docker.
    ``raising`` names one that raises a FOREIGN ``RuntimeError`` instead —
    the shape a bug or an unwrapped subprocess error takes.
    """

    def __init__(self, failing: str | None = None, raising: str | None = None) -> None:
        self.calls: list[str] = []
        self.health_polls: list[str] = []
        self.failing = failing
        self.raising = raising

    def _record(self, name: str) -> int:
        self.calls.append(name)
        if name == self.failing:
            raise ActionFailed(name, 2, f"simulated {name} failure")
        if name == self.raising:
            raise RuntimeError(f"simulated foreign exception in {name}")
        return 0

    def reload(self, clone: Path) -> int:
        return self._record("reload")

    def rebuild(self, clone: Path) -> int:
        return self._record("rebuild")

    def migrate(self, container: str) -> int:
        return self._record("migrate")

    def npm_build(self, container: str) -> int:
        return self._record("npm_build")

    def wait_healthy(self, container: str, timeout: int = 600) -> None:
        self.health_polls.append(container)

    def as_actions(self) -> Actions:
        return Actions(
            reload=self.reload,
            rebuild=self.rebuild,
            migrate=self.migrate,
            npm_build=self.npm_build,
            wait_healthy=self.wait_healthy,
        )


class RecordingCards:
    """A :class:`CardFiler` that remembers what the engine asked it to file.

    ``reject_first`` makes the first N ``file_blocked`` calls answer False —
    a board outage during the tick that files — so the engine's "remember
    only what the board accepted" clause can be exercised for real.
    """

    def __init__(self, reject_first: int = 0) -> None:
        self.filed: list[tuple[str, str]] = []
        self.resolved: list[str] = []
        self.reject_first = reject_first

    def file_blocked(self, card_id: str, title: str, note: str, blocker: str) -> bool:
        self.filed.append((card_id, blocker))
        return len(self.filed) > self.reject_first

    def resolve(self, card_id: str, note: str) -> bool:
        self.resolved.append(card_id)
        return True


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path: Path) -> Iterator[None]:
    """Point git at an empty global config so a host's signing/hook settings cannot leak in.

    Real env vars, restored on teardown (the same shape test_verb_renames.py
    uses for XDG_RUNTIME_DIR); the engine's own ``git`` subprocesses inherit them.
    """
    empty = tmp_path / "gitconfig.empty"
    empty.write_text("", encoding="utf-8")
    previous = {
        k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")
    }
    os.environ["GIT_CONFIG_GLOBAL"] = str(empty)
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    yield
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def repos(tmp_path: Path) -> Repos:
    """A bare origin on ``develop``, the preview clone, and a writer clone."""
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "--quiet", "-b", "develop")
    _identify(seed)
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "--quiet", "-m", "seed")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "--quiet", "--bare", str(seed), str(origin))
    clone = tmp_path / "clone"
    writer = tmp_path / "writer"
    for target in (clone, writer):
        _git(
            tmp_path,
            "clone",
            "--quiet",
            "--branch",
            "develop",
            str(origin),
            str(target),
        )
        _identify(target)
    return Repos(
        origin=origin, clone=clone, writer=writer, state_dir=tmp_path / "state"
    )


def _config(
    repos: Repos,
    actions: RecordingActions | None = None,
    cards: RecordingCards | None = None,
    dry_run: bool = False,
) -> Config:
    return Config(
        clone=repos.clone,
        state_dir=repos.state_dir,
        actions=(actions or RecordingActions()).as_actions(),
        cards=cards or RecordingCards(),
        dry_run=dry_run,
    )


def _baseline(repos: Repos) -> Outcome:
    """The first tick: records HEAD as applied so later ticks have a diff base."""
    return sync(_config(repos))


def test_first_run_records_head_as_applied_and_is_noop(repos: Repos):
    """With no state the tick records the baseline and does nothing else."""
    # Arrange
    head = repos.head()
    # Act
    outcome = sync(_config(repos))
    # Assert
    assert (outcome.status, repos.state()["applied_head"]) == ("noop", head)


def test_python_commit_is_fast_forwarded_and_recorded_without_actions(repos: Repos):
    """A ``.py`` change is live by autoreload: HEAD moves, applied_head follows, nothing runs."""
    # Arrange
    _baseline(repos)
    new_head = repos.push("apps/x/views.py")
    recorder = RecordingActions()
    # Act
    outcome = sync(_config(repos, actions=recorder))
    # Assert
    assert (
        repos.head(),
        repos.state()["applied_head"],
        outcome.status,
        recorder.calls,
    ) == (
        new_head,
        new_head,
        "noop",
        [],
    )


@pytest.mark.parametrize(
    "relpath,expected_calls",
    [
        (DOCKERFILE, ["rebuild"]),
        ("static/ts/app.ts", ["npm_build"]),
        (COMPOSE, ["reload"]),
        ("apps/x/migrations/0002_more.py", ["migrate"]),
    ],
)
def test_commit_triggers_exactly_the_follow_up_it_needs(
    repos: Repos, relpath: str, expected_calls: list[str]
):
    """One changed file, one action — the recorder proves the callable ran once."""
    # Arrange
    _baseline(repos)
    repos.push(relpath)
    recorder = RecordingActions()
    # Act
    outcome = sync(_config(repos, actions=recorder))
    # Assert
    assert (recorder.calls, outcome.status) == (expected_calls, "ok")


def test_container_health_is_awaited_after_a_recreate(repos: Repos):
    """A reload without a health wait would hand the next tick a half-booted container."""
    # Arrange
    _baseline(repos)
    repos.push(COMPOSE)
    recorder = RecordingActions()
    # Act
    sync(_config(repos, actions=recorder))
    # Assert
    assert recorder.health_polls == ["scitex-hub-dev-django-1"]


def test_tracked_dirt_refuses_and_leaves_head_alone(repos: Repos):
    """An operator's half-finished edit is never clobbered by a fast-forward."""
    # Arrange
    _baseline(repos)
    old_head = repos.head()
    repos.push("apps/x/views.py")
    (repos.clone / "README.md").write_text(
        "operator edit in progress\n", encoding="utf-8"
    )
    # Act
    outcome = sync(_config(repos))
    # Assert
    assert (outcome.status, repos.head()) == ("refused", old_head)


def test_diverging_local_commit_is_refused(repos: Repos):
    """A clone with its own commits cannot fast-forward and must not be reset."""
    # Arrange
    _baseline(repos)
    (repos.clone / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repos.clone, "add", "local.txt")
    _git(repos.clone, "commit", "--quiet", "-m", "local divergence")
    repos.push("apps/x/views.py")
    # Act
    outcome = sync(_config(repos))
    # Assert
    assert outcome.status == "refused"


def test_refusal_files_one_operator_decision_card(repos: Repos):
    """A stuck clone must reach a human through the board, once per head."""
    # Arrange
    _baseline(repos)
    (repos.clone / "README.md").write_text("dirty\n", encoding="utf-8")
    cards = RecordingCards()
    # Act
    for _ in range(3):
        sync(_config(repos, cards=cards))
    # Assert
    assert cards.filed == [(CARD_CLONE_REFUSED, "operator-decision")]


def test_failing_rebuild_twice_holds_the_head_without_a_third_call(repos: Repos):
    """After ``max_attempts`` failures the head is HELD; the action is not retried forever."""
    # Arrange
    _baseline(repos)
    repos.push(DOCKERFILE)
    recorder = RecordingActions(failing="rebuild")
    # Act
    outcomes = [sync(_config(repos, actions=recorder)) for _ in range(3)]
    # Assert
    assert ([o.status for o in outcomes], recorder.calls) == (
        ["failed", "failed", "held"],
        ["rebuild", "rebuild"],
    )


def test_held_head_files_exactly_one_card(repos: Repos):
    """Holding is reported on the board once, not once per 2-minute tick."""
    # Arrange
    _baseline(repos)
    repos.push(DOCKERFILE)
    recorder = RecordingActions(failing="rebuild")
    cards = RecordingCards()
    # Act
    for _ in range(4):
        sync(_config(repos, actions=recorder, cards=cards))
    # Assert
    assert cards.filed == [(CARD_SYNC_FAILED, "dependency")]


def test_success_at_a_later_head_resolves_the_held_card(repos: Repos):
    """A new commit that applies cleanly closes the card the held one opened."""
    # Arrange
    _baseline(repos)
    repos.push(DOCKERFILE)
    cards = RecordingCards()
    failing = RecordingActions(failing="rebuild")
    for _ in range(3):
        sync(_config(repos, actions=failing, cards=cards))
    repos.push("apps/x/views.py")
    # Act
    outcome = sync(_config(repos, actions=RecordingActions(), cards=cards))
    # Assert
    assert (outcome.status, cards.resolved) == ("ok", [CARD_SYNC_FAILED])


def test_second_sync_while_the_lock_is_held_reports_already_running(repos: Repos):
    """A manual run and a timer run must never interleave on the same clone."""
    # Arrange
    repos.state_dir.mkdir(parents=True, exist_ok=True)
    holder = (repos.state_dir / LOCK_FILE).open("a+")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        # Act
        outcome = sync(_config(repos))
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()
    # Assert
    assert (outcome.status, outcome.exit_code) == ("already_running", 0)


def test_dry_run_fetches_but_does_not_move_head(repos: Repos):
    """The plan must be real (fetched) while the clone stays exactly where it was."""
    # Arrange
    _baseline(repos)
    old_head = repos.head()
    new_head = repos.push(DOCKERFILE)
    # Act
    outcome = sync(_config(repos, dry_run=True))
    # Assert
    assert (
        _git(repos.clone, "rev-parse", "origin/develop"),
        repos.head(),
        outcome.status,
        outcome.plan.actions() if outcome.plan else None,
    ) == (new_head, old_head, "dry_run", ("rebuild",))


def test_outcome_json_carries_status_and_exit_code(repos: Repos):
    """stdout is the only contract the supervisor and an operator share."""
    # Arrange
    outcome = sync(_config(repos))
    # Act
    payload = json.loads(outcome.to_json())
    # Assert
    assert (payload["status"], payload["exit_code"]) == ("noop", 0)


def test_action_raising_a_foreign_exception_still_counts_toward_the_hold(
    repos: Repos,
):
    """A RuntimeError out of an action is a failed attempt, not a bypass of the gate."""
    # Arrange
    _baseline(repos)
    repos.push(DOCKERFILE)
    recorder = RecordingActions(raising="rebuild")
    # Act
    outcomes = [sync(_config(repos, actions=recorder)) for _ in range(3)]
    # Assert
    assert ([o.status for o in outcomes], recorder.calls) == (
        ["failed", "failed", "held"],
        ["rebuild", "rebuild"],
    )


def test_tick_killed_by_timeout_mid_action_counts_as_an_attempt(
    repos: Repos, tmp_path: Path
):
    """``/usr/bin/timeout`` SIGTERMs the tick during a slow rebuild; state must remember it."""
    # Arrange
    _baseline(repos)
    head = repos.push(DOCKERFILE)
    driver = tmp_path / "slow_tick.py"
    driver.write_text(SLOW_TICK_DRIVER, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(WORKTREE_SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    # Act
    completed = subprocess.run(
        [
            "/usr/bin/timeout",
            "3",
            sys.executable,
            str(driver),
            str(repos.clone),
            str(repos.state_dir),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    attempt = repos.state()["attempts"].get(head, {})
    # Assert
    assert (
        completed.returncode,
        attempt.get("action"),
        attempt.get("count"),
        attempt.get("rc"),
    ) == (124, "rebuild", 1, RC_KILLED), (completed.stdout, completed.stderr)


def test_local_commit_with_unchanged_origin_is_refused_without_actions(repos: Repos):
    """A clone AHEAD of origin is not a crash-resume: nothing runs, a human is asked."""
    # Arrange
    _baseline(repos)
    dockerfile = repos.clone / DOCKERFILE
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text("FROM local-edit\n", encoding="utf-8")
    _git(repos.clone, "add", "--all")
    _git(repos.clone, "commit", "--quiet", "-m", "operator's local Dockerfile edit")
    recorder = RecordingActions()
    # Act
    outcome = sync(_config(repos, actions=recorder))
    # Assert
    assert (outcome.status, recorder.calls) == ("refused", [])


def test_origin_force_pushed_backwards_is_refused_not_up_to_date(repos: Repos):
    """A commit removed from develop must not keep serving as 'up to date' forever."""
    # Arrange
    seed = repos.head()
    _baseline(repos)
    repos.push("apps/x/views.py")
    sync(_config(repos))
    repos.force_push_back_to(seed)
    cards = RecordingCards()
    # Act
    outcome = sync(_config(repos, cards=cards))
    # Assert
    assert (outcome.status, cards.filed) == (
        "refused",
        [(CARD_CLONE_REFUSED, "operator-decision")],
    )


def test_dry_run_says_would_refuse_for_a_clone_off_origin(repos: Repos):
    """The operator's preview of a tick must not promise a fast-forward that will be refused."""
    # Arrange
    _baseline(repos)
    (repos.clone / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repos.clone, "add", "local.txt")
    _git(repos.clone, "commit", "--quiet", "-m", "local divergence")
    repos.push(DOCKERFILE)
    # Act
    outcome = sync(_config(repos, dry_run=True))
    # Assert
    assert (
        outcome.status,
        outcome.message.startswith("would REFUSE"),
        outcome.plan,
    ) == ("dry_run", True, None)


def test_non_ascii_typescript_path_still_triggers_npm_build(repos: Repos):
    """git quotes non-ASCII paths unless asked for -z; the bundle must still rebuild."""
    # Arrange
    _baseline(repos)
    repos.push("static/ts/ウィジェット.ts")
    recorder = RecordingActions()
    # Act
    outcome = sync(_config(repos, actions=recorder))
    # Assert
    assert (recorder.calls, outcome.status) == (["npm_build"], "ok")


def test_card_rejected_by_the_board_is_filed_again_next_tick(repos: Repos):
    """A board outage during the filing tick must not mark the card as filed."""
    # Arrange
    _baseline(repos)
    head = repos.head()
    (repos.clone / "README.md").write_text("dirty\n", encoding="utf-8")
    cards = RecordingCards(reject_first=1)
    # Act
    for _ in range(3):
        sync(_config(repos, cards=cards))
    # Assert
    assert (len(cards.filed), repos.state()["filed_cards"][CARD_CLONE_REFUSED]) == (
        2,
        head,
    )


def test_fetch_failure_does_not_consume_a_rebuild_attempt(repos: Repos):
    """Attempts are per HEAD and per cause; a network blip is not a second rebuild failure."""
    # Arrange
    _baseline(repos)
    repos.push(DOCKERFILE)
    recorder = RecordingActions(failing="rebuild")
    statuses = [sync(_config(repos, actions=recorder)).status]
    url = repos.break_remote()
    statuses.append(sync(_config(repos, actions=recorder)).status)
    repos.restore_remote(url)
    # Act
    statuses += [sync(_config(repos, actions=recorder)).status for _ in range(2)]
    # Assert
    assert (statuses, recorder.calls.count("rebuild")) == (
        ["failed", "failed", "failed", "held"],
        2,
    )


def test_recovered_fetch_resolves_its_card_even_with_nothing_new(repos: Repos):
    """The fetch card closes when fetch works again, not when an unrelated commit lands."""
    # Arrange
    _baseline(repos)
    cards = RecordingCards()
    url = repos.break_remote()
    for _ in range(2):
        sync(_config(repos, cards=cards))
    repos.restore_remote(url)
    # Act
    outcome = sync(_config(repos, cards=cards))
    # Assert
    assert (outcome.status, cards.filed, cards.resolved) == (
        "noop",
        [(CARD_FETCH_FAILED, "dependency")],
        [CARD_FETCH_FAILED],
    )


def test_unknown_applied_head_is_rebaselined_instead_of_failing_forever(
    repos: Repos,
):
    """State from another clone must not make every tick exit 1 until a human notices."""
    # Arrange
    _baseline(repos)
    stale = repos.state()
    stale["applied_head"] = "0" * 40
    (repos.state_dir / "state.json").write_text(json.dumps(stale), encoding="utf-8")
    new_head = repos.push("apps/x/views.py")
    # Act
    statuses = [sync(_config(repos)).status for _ in range(2)]
    # Assert
    assert (statuses, repos.state()["applied_head"]) == (["noop", "noop"], new_head)


def test_success_prunes_attempts_of_superseded_heads(repos: Repos):
    """state.json must not grow by one record per failing head for the life of the job."""
    # Arrange
    _baseline(repos)
    repos.push(DOCKERFILE)
    failing = RecordingActions(failing="rebuild")
    for _ in range(3):
        sync(_config(repos, actions=failing))
    repos.push("apps/x/views.py")
    # Act
    sync(_config(repos, actions=RecordingActions()))
    # Assert
    assert repos.state()["attempts"] == {}


# EOF
