#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_figrecipe_wrapper_authorization.py
"""Authorization regression: the figrecipe mount's path jail, END TO END.

WHY THIS FILE EXISTS (and why the sibling file was not enough)
--------------------------------------------------------------
``deployment/docker/common/nginx/nginx_prod.conf`` carried an edge
tourniquet::

    location /apps/figrecipe/figrecipe/ { return 403; }

added 2026-07-24 when the wrapper had NO ``@login_required`` and honoured a
caller-supplied ``?working_dir=``. The code fix shipped weeks later, but the
edge block stayed on for 3.5 more weeks because NOTHING went red to say it
was redundant — and, worse, nothing would have gone red on the day someone
deleted it either. An nginx ``return 403`` stops guarding the instant a conf
file is edited, and no test in this repo can tell.

So this suite replaces an EDGE rule with an AUTHORIZATION assertion. It says
nothing whatsoever about nginx. It drives the REAL routed URLs through the
REAL urlconf with the REAL Django test client, as a REAL logged-in ``User``
who owns a REAL ``Project`` on a REAL directory, and asserts the wrapper
fails closed on every one of figrecipe's three injection channels. If the
guard is removed, these go red; the edge rule is then free to go.

WHY NOT JUST EXTEND tests/security/test_working_dir_passthrough.py
------------------------------------------------------------------
That file covers the same three channels, and it is a good file — but every
one of its tests CONSTRUCTS ITS OWN ``WorkingDirScopedView(recorder,
resolver=..., guard=figrecipe_urls._reject_out_of_jail_paths)``. It proves
the guard FUNCTION is correct when someone wires it up. It cannot notice if
the module stops wiring it up: delete ``guard=`` from the real ``_api_view``
at figrecipe.py, or drop ``@login_required``, or unmount the route, and all
of those tests still pass. That is precisely the failure shape
``tests/develop/test_guards_declare_their_defect.py`` was written about —
asserting the artefact the author edited rather than the thing that runs.
This file asserts the thing that runs: URL in, status code out.

THE THREE CHANNELS (from the wrapper's own module docstring)
------------------------------------------------------------
  CHANNEL 1+2  query/body params joined to working_dir: ``path``,
               ``recipe``, ``recipe_path``. ``pathlib``'s ``/`` DISCARDS the
               left operand when the right side is ABSOLUTE, so an absolute
               value escapes the server-forced working_dir; a relative
               ``../`` value climbs out.
  CHANNEL 2    endpoint-gated body sinks whose base is NOT working_dir:
               ``api/compose`` (body working_dir verbatim -> arbitrary
               WRITE), ``api/gallery/add`` (``template`` -> package-dir
               read), ``add_image_from_url`` (``file://`` -> local read).
  CHANNEL 3    the URL ``<path:endpoint>`` SEGMENT, which no query/body
               guard ever sees: ``api/file-content/<remainder>`` and
               ``api/gallery/thumbnail/<name>``.

A guard covering two of the three is what the upstream package already had.

EXPECTED VALUES ARE MEASURED, NOT GUESSED
------------------------------------------
Every status code below was measured live on production 2026-08-17,
authenticated as a visitor, with nginx bypassed. Two measurement traps are
pinned as tests of their own so nobody re-hits them:

  * ``api/file-content/AGENTS.md`` (BARE filename) is CORRECTLY 403 — the
    remainder resolves against BASE_DIR, i.e. ``/app/AGENTS.md``, which is
    outside every tenant's jail. Used as a positive control it looks like
    the guard over-blocks. The real in-jail form is
    ``api/file-content/data/users/<user>/proj/<project>/AGENTS.md``.
    ``test_bare_filename_remainder_is_403_because_it_resolves_outside_the_jail``
    pins that this 403 is intended.
  * ``curl`` normalises ``../`` CLIENT-SIDE per RFC 3986, so a traversal
    probe never reaches Django and returns 301, which reads as a pass.
    Django's test client sends the path verbatim — one more reason this
    suite uses it rather than an HTTP probe.

NO MOCKS (STX-NM001/003): real client, real ``User``, real ``Project``, real
directories under the real ``BASE_DIR/data/users/`` jail. The only patched
value is the ``FIGRECIPE_WORKING_DIR`` env var, set to ``BASE_DIR`` to
reproduce the container's implicit ``cwd == /app == BASE_DIR`` — that is
configuring the real package the way production configures it, not
substituting it.

ONE ASSERT PER TEST (STX-TQ007), AAA markers (STX-TQ002). Setup lives in
fixtures; each test name states the single property it pins.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client

from apps.infra.project_app.models import Project

pytestmark = [
    pytest.mark.security,
    pytest.mark.django_db,
    pytest.mark.guards(
        defect=(
            "The figrecipe mount /apps/figrecipe/figrecipe/ can silently stop "
            "authorizing: its path jail lives in a wrapper guard that a "
            "refactor can unwire (or a nginx 'return 403' someone deletes), "
            "letting a caller-controlled path in the query string, the JSON "
            "body or the URL <path:endpoint> segment escape the caller's own "
            "data root and read or write another tenant's files."
        )
    ),
]

# The REAL routed prefix: config/urls.py mounts figrecipe_app at
# "apps/figrecipe/", and urls/figrecipe.py routes "figrecipe/<path:endpoint>".
MOUNT = "/apps/figrecipe/figrecipe/"

CALLER = "figjail-caller"
VICTIM = "figjail-victim"

# Content proving a 200 carried the caller's OWN file, not an empty shell.
CALLER_SENTINEL = "figrecipe-jail-positive-control-sentinel"
VICTIM_SENTINEL = "figrecipe-jail-victim-only-sentinel"

# The canonical fail-closed body the wrapper returns on any escape.
FORBIDDEN_MESSAGE = "path is outside your workspace"


# ---------------------------------------------------------------------------
# Fixtures — real users, real projects, real directories (no mocks)
# ---------------------------------------------------------------------------
def _data_root() -> Path:
    """The jail root the production permission check uses verbatim."""
    return Path(settings.BASE_DIR) / "data" / "users"


def _make_tenant(username: str, sentinel: str, slug: str) -> tuple[User, Path]:
    """Create a real User + Project on a real dir inside that user's jail.

    ``last_active_repository`` is set deliberately. Creating a ``User`` fires
    the real accounts_app signals, which provision a home ``dotfiles`` project
    and adopt it as the landing project; ``get_current_project`` then gives
    that HIGHEST priority and the project made here would never be selected.
    Pointing the profile at it is exactly what the header project selector
    does for a real user, so this is the app's own mechanism, not a bypass.
    """
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="Password123!",  # pragma: allowlist secret
    )
    project_dir = _data_root() / username / "proj" / "p1"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "AGENTS.md").write_text(sentinel + "\n", encoding="utf-8")
    project = Project.objects.create(
        owner=user,
        name="P1",
        slug=slug,
        local_path=str(project_dir),
    )
    user.profile.last_active_repository = project
    user.profile.save(update_fields=["last_active_repository"])
    return user, project_dir


@pytest.fixture(autouse=True)
def figrecipe_base_matches_base_dir():
    """Pin the package's own file-content base to BASE_DIR.

    ``handle_api_file_content`` resolves its remainder against
    ``_find_default_working_dir()``, which is ``FIGRECIPE_WORKING_DIR`` or
    the process cwd. In the container that cwd IS ``/app`` == ``BASE_DIR``,
    which is the arrangement the wrapper's Channel-3 check is written
    against. Setting the env var reproduces prod exactly instead of leaving
    the suite dependent on which directory pytest was invoked from.

    Plain ``os.environ`` + teardown, not the ``monkeypatch`` fixture
    (STX-NM002): this configures the REAL package through its REAL public
    knob, the same one the container sets. Nothing is substituted.
    """
    previous = os.environ.get("FIGRECIPE_WORKING_DIR")
    os.environ["FIGRECIPE_WORKING_DIR"] = str(settings.BASE_DIR)
    yield
    if previous is None:
        os.environ.pop("FIGRECIPE_WORKING_DIR", None)
    else:
        os.environ["FIGRECIPE_WORKING_DIR"] = previous


@pytest.fixture
def caller_project_dir():
    """The logged-in caller's own project directory (cleaned up after)."""
    _user, project_dir = _make_tenant(CALLER, CALLER_SENTINEL, "figjail-p-caller")
    yield project_dir
    shutil.rmtree(_data_root() / CALLER, ignore_errors=True)


@pytest.fixture
def victim_project_dir():
    """A SECOND tenant's directory — the cross-tenant read target."""
    _user, project_dir = _make_tenant(VICTIM, VICTIM_SENTINEL, "figjail-p-victim")
    yield project_dir
    shutil.rmtree(_data_root() / VICTIM, ignore_errors=True)


@pytest.fixture
def client(caller_project_dir):
    """A REAL Django test client logged in as the caller."""
    http = Client()
    http.force_login(User.objects.get(username=CALLER))
    return http


@pytest.fixture
def anon_client():
    """A REAL client with no session at all."""
    return Client()


def _segment(project_dir: Path) -> str:
    """The BASE_DIR-relative segment form ``api/file-content`` expects."""
    return str(project_dir.relative_to(Path(settings.BASE_DIR)))


def _post(http: Client, endpoint: str, body: dict):
    """POST a JSON body to a figrecipe endpoint through the real route."""
    return http.post(
        MOUNT + endpoint,
        data=json.dumps(body),
        content_type="application/json",
    )


# ===========================================================================
# GATE 0 — authentication. Anonymous must never reach the dispatcher.
# ===========================================================================
def test_anonymous_api_request_is_redirected(anon_client):
    # Arrange
    url = MOUNT + "api/tree"
    # Act
    response = anon_client.get(url)
    # Assert
    assert response.status_code == 302


def test_anonymous_api_request_is_redirected_to_the_login_page(anon_client):
    # Arrange
    url = MOUNT + "api/tree"
    # Act
    response = anon_client.get(url)
    # Assert
    assert response.headers["Location"].startswith("/auth/login/")


def test_anonymous_editor_page_is_redirected(anon_client):
    # Arrange
    url = MOUNT
    # Act
    response = anon_client.get(url)
    # Assert
    assert response.status_code == 302


# ===========================================================================
# CHANNEL 1+2 — query / body params joined to working_dir
# ===========================================================================
def test_absolute_path_query_param_is_403(client):
    # Arrange
    url = MOUNT + "api/switch"
    # Act
    response = client.get(url, {"path": "/etc/passwd"})
    # Assert
    assert response.status_code == 403


def test_absolute_path_query_param_403_names_the_workspace(client):
    # Arrange
    url = MOUNT + "api/switch"
    # Act
    response = client.get(url, {"path": "/etc/passwd"})
    # Assert
    assert json.loads(response.content)["error"] == FORBIDDEN_MESSAGE


def test_absolute_recipe_query_param_is_403(client):
    # Arrange — ``recipe`` is opened VERBATIM by the editor bootstrap
    url = MOUNT + "api/switch"
    # Act
    response = client.get(url, {"recipe": "/etc/passwd"})
    # Assert
    assert response.status_code == 403


def test_relative_traversal_recipe_query_param_is_403(client):
    # Arrange — ``..`` climbs out even though the value is not absolute
    url = MOUNT + "api/switch"
    # Act
    response = client.get(url, {"recipe": "../../../../../../etc/passwd"})
    # Assert
    assert response.status_code == 403


def test_absolute_path_json_body_is_403(client):
    # Arrange — the GET override never touches the JSON body
    # Act
    response = _post(client, "api/switch", {"path": "/etc/passwd"})
    # Assert
    assert response.status_code == 403


def test_relative_traversal_path_json_body_is_403(client):
    # Arrange
    # Act
    response = _post(client, "api/switch", {"path": "../../../../../../etc/passwd"})
    # Assert
    assert response.status_code == 403


def test_absolute_recipe_path_json_body_is_403(client):
    # Arrange — ``recipe_path`` is the body spelling of ``recipe``
    # Act
    response = _post(client, "api/switch", {"recipe_path": "/etc/passwd"})
    # Assert
    assert response.status_code == 403


def test_cross_tenant_absolute_path_query_param_is_403(client, victim_project_dir):
    # Arrange — an absolute path INSIDE another live tenant, not /etc
    url = MOUNT + "api/switch"
    victim_file = str(victim_project_dir / "AGENTS.md")
    # Act
    response = client.get(url, {"path": victim_file})
    # Assert
    assert response.status_code == 403


# ===========================================================================
# CHANNEL 1+2 — the working_dir OVERRIDE itself
# ===========================================================================
def test_caller_supplied_working_dir_is_still_served(client):
    # Arrange — the override discards the value; it does not reject the call
    url = MOUNT + "api/tree"
    # Act
    response = client.get(url, {"working_dir": "/tmp"})
    # Assert
    assert response.status_code == 200


def test_caller_supplied_working_dir_is_overwritten_with_the_own_project(
    client, caller_project_dir
):
    # Arrange
    url = MOUNT + "api/tree"
    # Act
    response = client.get(url, {"working_dir": "/tmp"})
    # Assert — the listing is rooted at the caller's OWN project, never /tmp
    assert json.loads(response.content)["working_dir"] == str(caller_project_dir)


def test_caller_supplied_working_dir_never_lists_the_requested_directory(client):
    # Arrange — the 200 above must not be mistaken for "it listed /tmp"
    url = MOUNT + "api/tree"
    # Act
    response = client.get(url, {"working_dir": "/tmp"})
    # Assert
    assert json.loads(response.content)["working_dir"] != "/tmp"


# ===========================================================================
# CHANNEL 2 — endpoint-gated body sinks (base is NOT working_dir)
# ===========================================================================
def test_compose_absolute_body_working_dir_write_is_403(client):
    # Arrange — handle_compose_save writes Path(body working_dir)/f"{name}.png"
    body = {"working_dir": "/tmp", "filename": "pwned"}
    # Act
    response = _post(client, "api/compose", body)
    # Assert
    assert response.status_code == 403


def test_compose_traversal_in_filename_write_is_403(client):
    # Arrange — in-jail working_dir, but ``..`` in filename escapes it
    body = {"working_dir": str(_data_root() / CALLER), "filename": "../../pwned"}
    # Act
    response = _post(client, "api/compose", body)
    # Assert — the EXACT resolved out-path is what gets validated
    assert response.status_code == 403


def test_gallery_add_template_traversal_is_403(client):
    # Arrange — ``template`` reads _EXAMPLES_DIR / f"{template}.yaml"
    body = {"template": "../../../../etc/passwd"}
    # Act
    response = _post(client, "api/gallery/add", body)
    # Assert
    assert response.status_code == 403


def test_gallery_add_absolute_template_is_403(client):
    # Arrange
    body = {"template": "/etc/passwd"}
    # Act
    response = _post(client, "api/gallery/add", body)
    # Assert
    assert response.status_code == 403


def test_add_image_from_url_file_scheme_is_403(client):
    # Arrange — urllib.urlopen honours file://, i.e. an arbitrary local READ
    body = {"url": "file:///etc/passwd"}
    # Act
    response = _post(client, "add_image_from_url", body)
    # Assert
    assert response.status_code == 403


def test_add_image_from_url_non_http_scheme_is_403(client):
    # Arrange — the check is an ALLOWLIST of http(s), not a file:// denylist
    body = {"url": "ftp://example.com/x.png"}
    # Act
    response = _post(client, "add_image_from_url", body)
    # Assert
    assert response.status_code == 403


# ===========================================================================
# CHANNEL 3 — the URL <path:endpoint> SEGMENT
# ===========================================================================
def test_file_content_segment_traversal_is_403(client):
    # Arrange — Django's test client sends ``..`` verbatim (curl would not)
    url = MOUNT + "api/file-content/../../../../etc/passwd"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 403


def test_file_content_segment_absolute_remainder_is_403(client):
    # Arrange — a leading slash makes the remainder ABSOLUTE, so pathlib
    # discards the BASE_DIR base entirely.
    url = MOUNT + "api/file-content//etc/passwd"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 403


def test_file_content_segment_cross_tenant_read_is_403(client, victim_project_dir):
    # Arrange — the package's own jail is a startswith(BASE_DIR) that
    # CONTAINS every tenant, so only the wrapper stops this one.
    url = MOUNT + "api/file-content/" + _segment(victim_project_dir) + "/AGENTS.md"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 403


def test_file_content_segment_cross_tenant_read_leaks_no_content(
    client, victim_project_dir
):
    # Arrange
    url = MOUNT + "api/file-content/" + _segment(victim_project_dir) + "/AGENTS.md"
    # Act
    response = client.get(url)
    # Assert — status codes can be right while the body still leaks
    assert VICTIM_SENTINEL not in response.content.decode("utf-8", "replace")


def test_bare_filename_remainder_is_403_because_it_resolves_outside_the_jail(client):
    # Arrange — MEASUREMENT TRAP: the remainder is relative to BASE_DIR, so
    # a bare name is /app/AGENTS.md, correctly outside every tenant jail.
    # Pinned so a future reader does not file this 403 as an over-block.
    url = MOUNT + "api/file-content/AGENTS.md"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 403


def test_gallery_thumbnail_segment_traversal_is_403(client):
    # Arrange — ``..`` climbs out of the read-only package examples dir
    url = MOUNT + "api/gallery/thumbnail/../../../../etc/passwd"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 403


def test_gallery_thumbnail_segment_absolute_name_is_403(client):
    # Arrange
    url = MOUNT + "api/gallery/thumbnail//etc/passwd"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 403


# ===========================================================================
# POSITIVE CONTROLS — without these the suite cannot tell "guard works"
# from "endpoint is dead", and "deny everything" would pass.
# ===========================================================================
def test_own_file_content_by_segment_is_served(client, caller_project_dir):
    # Arrange — the CORRECT in-jail form: BASE_DIR-relative, under the
    # caller's own data/users/<user>/proj/<project>/ root.
    url = MOUNT + "api/file-content/" + _segment(caller_project_dir) + "/AGENTS.md"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 200


def test_own_file_content_by_segment_returns_the_real_content(
    client, caller_project_dir
):
    # Arrange — a 200 with an empty body would not prove the read happened
    url = MOUNT + "api/file-content/" + _segment(caller_project_dir) + "/AGENTS.md"
    # Act
    response = client.get(url)
    # Assert
    assert CALLER_SENTINEL in json.loads(response.content)["content"]


def test_api_files_is_served(client):
    # Arrange
    url = MOUNT + "api/files"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 200


def test_list_themes_is_served(client):
    # Arrange — an endpoint with no path input at all must stay reachable
    url = MOUNT + "list_themes"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 200


def test_api_gallery_is_served(client):
    # Arrange
    url = MOUNT + "api/gallery"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 200


def test_relative_in_jail_path_query_param_is_not_blocked(client):
    # Arrange — a normal relative recipe path inside the caller's project
    url = MOUNT + "api/switch"
    # Act
    response = client.get(url, {"path": "figures/fig1.yaml"})
    # Assert — whatever the handler answers, the GUARD must not 403 it
    assert response.status_code != 403


def test_relative_in_jail_path_json_body_is_not_blocked(client):
    # Arrange
    # Act
    response = _post(client, "api/switch", {"path": "figures/fig1.yaml"})
    # Assert
    assert response.status_code != 403


def test_http_image_url_is_not_blocked(client):
    # Arrange — the allowlist must admit the legitimate remote-fetch case.
    # A LOOPBACK url on the discard port: the guard only reads the SCHEME, and
    # the dispatcher short-circuits with "No recipe loaded" before the handler
    # would fetch anything, so this suite can never make network egress even
    # if a future figrecipe reorders those two steps.
    body = {"url": "http://127.0.0.1:9/x.png"}
    # Act
    response = _post(client, "add_image_from_url", body)
    # Assert
    assert response.status_code != 403


def test_plain_gallery_template_name_is_not_blocked(client):
    # Arrange — a well-formed RELATIVE template name, which is the shape the
    # guard's ``_within_relative_subtree`` check must admit. The name is
    # deliberately one that does not exist, so the handler answers 404 and
    # WRITES NOTHING: ``handle_gallery_add`` copies the template into
    # ``Path.cwd()`` when no editor is loaded — it ignores working_dir
    # entirely — so a real template name here drops a .yaml into the repo
    # root on every test run, in CI too. Reaching the handler at all is what
    # proves the guard let the value through, which is the property here.
    body = {"template": "no-such-template-figjail-probe"}
    # Act
    response = _post(client, "api/gallery/add", body)
    # Assert
    assert response.status_code != 403


def test_plain_gallery_thumbnail_name_is_not_blocked(client):
    # Arrange
    url = MOUNT + "api/gallery/thumbnail/plot_scatter"
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code != 403


def test_editor_page_is_served_to_a_logged_in_caller(client):
    # Arrange — the SPA shell itself must survive the login gate
    url = MOUNT
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 200


# EOF
