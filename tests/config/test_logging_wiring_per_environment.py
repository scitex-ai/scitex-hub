#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_logging_wiring_per_environment.py
"""Every DEPLOYED environment must keep the logging wiring the base sets up.

Operator request, Telegram 2026-08-10:
「サイテクスハブの ... 失敗っていうのは必ず私にメールが届くようにしてほしいんですよ」

TWO defects, one behind the other, both of which read as working config:

1. Until 2026-08-15 the ``mail_admins`` handler was DEFINED in
   ``settings_logging`` and referenced by no logger at all, so hub had never
   sent a single admin error email.
2. The first fix attached it to the loggers in ``settings_logging`` -- the BASE
   module -- and every deployed environment then threw that wiring away.
   ``settings_prod`` and ``settings_staging`` refined the base with
   ``LOGGING.update({... "loggers": {...} ...})``, and ``dict.update`` REPLACES
   a whole section. Measured against the real modules on 2026-08-15, composed
   production had four loggers, none of them on the rail, while ``mail_admins``
   was still defined -- the exact orphaned-handler defect fix 1 claimed to
   close, surviving untouched where it mattered.

Defect 2 shipped with a green gate, because that gate asserted against
``settings_logging`` loaded in isolation -- a dictionary no deployed process
ever uses. So THIS file composes the real
``config.settings.settings_{prod,staging,dev}`` and asserts on the dictionary
Django would actually hand to ``dictConfig``. One subprocess per environment,
because a deployed process loads exactly ONE settings module, and because every
environment module star-imports the same ``settings_shared``: importing two of
them in one interpreter measures their interference rather than either of them.

The requirements below are written HERE rather than imported from
``config.settings``. A gate that reads its own expectations out of the code
under test agrees with whatever that code says, including a deletion.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = REPO_ROOT / "config" / "settings"

# The handler that carries a failure out of the machine and to a person.
OPERATOR_RAIL_HANDLER = "mail_admins"

# Loggers that carry operational failure. Each must reach the operator in EVERY
# deployed environment. apps.infra.project_app carries the visitor-pool and
# template-clone path whose four-day silent failure motivated all of this.
LOGGERS_THAT_MUST_MAIL_ADMINS = (
    "django.request",
    "django.security",
    "scitex.errors",
    "apps.infra.project_app",
    "apps.workspace.writer_app",
    "apps.workspace.scholar_app",
    "apps.workspace.console_app",
)

# A handler may be referenced by no logger ONLY when something attaches it by
# name at runtime. Each entry needs a written reason. Deliberately kept in the
# test and not read from the settings, so silencing this gate requires editing
# the gate.
HANDLERS_ALLOWED_TO_HAVE_NO_LOGGER = {
    # A no-op sink attached on demand to silence a third-party logger.
    "null",
}

# Every settings module a deployment actually points DJANGO_SETTINGS_MODULE at
# (deployment/docker/docker-compose.{prod,staging}.yml, and
# docker-compose.override.yml for dev).
DEPLOYED_ENVIRONMENTS = ("settings_prod", "settings_staging", "settings_dev")

# Configuration these modules REQUIRE and refuse to boot without. Supplying it
# stubs nothing: these are operator-set values with no default by design ("no
# silent fallback"), and the wiring under test does not depend on their content.
#
# SCITEX_HUB_ENV matters more than it looks. Importing
# ``config.settings.settings_prod`` executes ``config/settings/__init__.py``
# first, and that module auto-loads an environment from SCITEX_HUB_ENV,
# defaulting to development. Leaving it unset imports settings_dev BEFORE
# settings_prod and measures a combination no deployment runs. The values below
# are the ones the compose files set.
REQUIRED_CONFIG = {
    "settings_prod": {
        "SCITEX_HUB_ENV": "prod",
        "SCITEX_HUB_DJANGO_SECRET_KEY": "test-only-never-a-real-secret",
        "SCITEX_HUB_GITEA_SSH_PORT": "22",
    },
    "settings_staging": {
        "SCITEX_HUB_ENV": "staging",
        "SCITEX_HUB_DJANGO_SECRET_KEY": "test-only-never-a-real-secret",
        "SCITEX_HUB_GITEA_SSH_PORT": "2232",
    },
    "settings_dev": {
        "SCITEX_HUB_ENV": "development",
        "SCITEX_HUB_DJANGO_SECRET_KEY": "test-only-never-a-real-secret",
        "SCITEX_HUB_GITEA_SSH_PORT_DEV": "2222",
    },
}

# The probe writes its answer to a FILE, never to stdout.
#
# It used to json.dump into sys.stdout, and settings_dev broke it: importing a
# settings module prints (Django checks, scitex banners, third-party warnings),
# so the JSON arrived with a prefix and json.loads died on "line 1 column 1"
# while the process still exited 0. The reader could not tell a polluted stream
# from a broken one. Stripping the noise would only work until something new
# printed — a dedicated channel is immune to anything an import decides to say.
_COMPOSE_PROBE = """
import importlib, json, sys

module = importlib.import_module("config.settings." + sys.argv[1])
config = module.LOGGING
payload = {
    "handlers": sorted(config.get("handlers", {})),
    "files": {
        name: str(handler["filename"])
        for name, handler in config.get("handlers", {}).items()
        if handler.get("filename")
    },
    "loggers": {
        name: list(logger.get("handlers", []))
        for name, logger in config.get("loggers", {}).items()
    },
    "root": list(config.get("root", {}).get("handlers", [])),
}
with open(sys.argv[2], "w", encoding="utf-8") as fh:
    json.dump(payload, fh)
"""


@lru_cache(maxsize=None)
def compose(settings_module: str) -> str:
    """The LOGGING dict Django would hand to dictConfig for this environment.

    Returned as JSON text because ``lru_cache`` must not hand out a mutable
    dict that one test could edit for the next.
    """
    environment = dict(os.environ)
    environment.update(REQUIRED_CONFIG[settings_module])
    # A documented operator override (settings_logging), used so that importing
    # settings does not create log directories inside the checkout.
    environment["SCITEX_HUB_LOG_DIR"] = tempfile.mkdtemp(prefix="hub-logging-gate-")
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    out_path = Path(environment["SCITEX_HUB_LOG_DIR"]) / "composed-logging.json"
    completed = subprocess.run(
        [sys.executable, "-c", _COMPOSE_PROBE, settings_module, str(out_path)],
        cwd=str(REPO_ROOT),
        env=environment,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"config.settings.{settings_module} could not be imported, so its "
            "logging wiring is UNGATED. This fails rather than skips on "
            "purpose: an environment nobody can compose is an environment "
            "nobody is checking, which is how mail_admins stayed dead for "
            f"months.\n--- stderr ---\n{completed.stderr}"
        )
    if not out_path.exists():
        # Exit 0 but no payload: the import succeeded and the probe still did
        # not answer. Distinguished from a parse failure on purpose — "I could
        # not tell" must never be reported as "the config is wrong".
        raise AssertionError(
            f"config.settings.{settings_module} imported cleanly but the probe "
            f"wrote no payload to {out_path}.\n"
            f"--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}"
        )
    return out_path.read_text(encoding="utf-8")


def composed(settings_module: str) -> dict:
    return json.loads(compose(settings_module))


@lru_cache(maxsize=None)
def base_logger_names() -> frozenset[str]:
    """The loggers ``settings_logging`` establishes, read from that module.

    This ONE expectation is read from the code under test, because the property
    it serves is inherently relative: an environment may ADD loggers, it may
    never lose one the base established. The absolute floor -- which loggers
    must reach the operator -- is the hardcoded tuple above, so deleting a
    logger from the base still fails this file rather than lowering the bar.

    Loaded by path, not imported: ``config/__init__.py`` pulls in celery_app,
    and ``config/settings/__init__.py`` auto-loads a whole environment.
    """
    log_dir_key = "SCITEX_HUB_LOG_DIR"
    previous = os.environ.get(log_dir_key)
    # settings_logging creates its log directory at import; keep that out of
    # the checkout. SCITEX_HUB_LOG_DIR is the documented operator override.
    os.environ[log_dir_key] = tempfile.mkdtemp(prefix="hub-logging-base-")
    try:
        path = SETTINGS_DIR / "settings_logging.py"
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return frozenset(module.LOGGING.get("loggers", {}))
    finally:
        if previous is None:
            del os.environ[log_dir_key]
        else:
            os.environ[log_dir_key] = previous


def _star_imports_shared(path: Path) -> bool:
    """True when this module composes the whole configuration.

    Read with ``ast`` rather than by substring: settings_static.py *mentions*
    ``from .settings_shared import *`` in its docstring while being a helper,
    not an environment.
    """
    for node in ast.walk(ast.parse(path.read_text())):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "settings_shared"
            and node.level == 1
            and any(alias.name == "*" for alias in node.names)
        ):
            return True
    return False


def _handlers_referenced(config: dict) -> set[str]:
    referenced: set[str] = set()
    for handlers in config["loggers"].values():
        referenced.update(handlers)
    referenced.update(config["root"])
    return referenced


@pytest.mark.parametrize("settings_module", DEPLOYED_ENVIRONMENTS)
class TestEveryDeployedEnvironmentIsWired:
    def test_the_operator_rail_handler_survives_composition(self, settings_module):
        # Arrange
        config = composed(settings_module)
        # Act
        defined = set(config["handlers"])
        # Assert
        assert OPERATOR_RAIL_HANDLER in defined, (
            f"COMPOSED {settings_module} has no {OPERATOR_RAIL_HANDLER!r} "
            "handler at all, so nothing in this environment can mail a failure."
        )

    def test_every_defined_handler_is_attached_to_a_logger(self, settings_module):
        # Arrange
        config = composed(settings_module)
        # Act
        orphaned = set(config["handlers"]) - _handlers_referenced(config)
        orphaned -= HANDLERS_ALLOWED_TO_HAVE_NO_LOGGER
        # Assert
        assert not orphaned, (
            f"In COMPOSED {settings_module} these handlers are defined and "
            f"referenced by no logger, so they never run: {sorted(orphaned)}. A "
            "handler that is configured but unattached reads as a working "
            "safety mechanism to anyone who greps for it while doing nothing at "
            "all. This is what an environment module does when it refines "
            "LOGGING with dict.update instead of "
            "config.settings._logging_merge.merge_logging: update REPLACES the "
            "loggers section and takes the base's wiring with it."
        )

    @pytest.mark.parametrize("logger_name", LOGGERS_THAT_MUST_MAIL_ADMINS)
    def test_failure_carrying_loggers_reach_the_operator(
        self, settings_module, logger_name
    ):
        # Arrange
        config = composed(settings_module)
        # Act
        handlers = config["loggers"].get(logger_name)
        # Assert
        assert handlers is not None, (
            f"COMPOSED {settings_module} has no logger {logger_name!r} at all. "
            "The base defines it; this environment discarded it."
        )
        assert OPERATOR_RAIL_HANDLER in handlers, (
            f"in COMPOSED {settings_module}, logger {logger_name!r} carries "
            f"operational failures but does not attach "
            f"{OPERATOR_RAIL_HANDLER!r} (it has {handlers}), so its errors reach "
            "a rotating log file and nobody else. This is how the visitor pool "
            "sat 14/16 quarantined for four days in August 2026."
        )

    def test_no_environment_silently_drops_a_base_logger(self, settings_module):
        """An environment may REFINE the base's logging, never delete part of it.

        Without this, an environment can keep the operator rail on the loggers
        this file happens to name while quietly discarding the rest, and the
        base stops being the source of truth that everyone reading it believes.
        """
        # Arrange
        config = composed(settings_module)
        required = base_logger_names() | set(LOGGERS_THAT_MUST_MAIL_ADMINS)
        # Act
        missing = required - set(config["loggers"])
        # Assert
        assert not missing, (
            f"COMPOSED {settings_module} has lost loggers that settings_logging "
            f"establishes: {sorted(missing)}. An environment refines the base; "
            "it does not get to delete part of it, because everything that "
            "reads the base believes those loggers are configured."
        )

    def test_no_two_handlers_write_to_the_same_file(self, settings_module):
        """One file, one writer.

        Two RotatingFileHandlers over one path rotate against each other: each
        renames the file the other still holds open, so lines land in a deleted
        inode and the backups overwrite one another. Until 2026-08-15 every
        environment defined BOTH the base's "django_file" and its own
        "file_django" over LOG_DIR/django.log; it stayed harmless only because
        the second one was orphaned, which is not a property to rely on.
        """
        # Arrange
        config = composed(settings_module)
        writers = defaultdict(list)
        for handler_name, filename in config["files"].items():
            writers[filename].append(handler_name)
        # Act
        shared = {
            filename: sorted(names)
            for filename, names in writers.items()
            if len(names) > 1
        }
        # Assert
        assert not shared, (
            f"In COMPOSED {settings_module} these log files have more than one "
            f"handler writing to them: {shared}. Two RotatingFileHandlers on "
            "one path rotate against each other and lose records. Refine the "
            "base's handler entry instead of adding a second one under a new "
            "name."
        )


class TestEveryEnvironmentIsCovered:
    """A new environment must not be able to slip past this file unnoticed."""

    def test_every_environment_settings_module_is_gated(self):
        """DEPLOYED_ENVIRONMENTS must name every real environment module.

        An environment module is one that composes the whole configuration by
        star-importing settings_shared -- that is exactly the shape that binds
        the base LOGGING and can then discard it. Adding
        ``settings_nas.py`` (planned) without adding it here would leave the
        new environment ungated, which is how this defect reached production
        the first time.
        """
        # Arrange
        candidates = sorted(SETTINGS_DIR.glob("settings_*.py"))
        # Act
        environments = {
            path.stem for path in candidates if _star_imports_shared(path)
        }
        # Assert
        assert environments == set(DEPLOYED_ENVIRONMENTS), (
            "the environments this gate checks "
            f"({sorted(DEPLOYED_ENVIRONMENTS)}) are not the environment "
            f"modules that exist ({sorted(environments)}). Add the new module "
            "to DEPLOYED_ENVIRONMENTS with the configuration it requires, or "
            "its logging wiring is checked by nobody."
        )


# EOF
