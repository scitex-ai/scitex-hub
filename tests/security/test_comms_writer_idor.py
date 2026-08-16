"""Mechanical regression barrier for three confirmed cross-tenant IDOR holes.

Found by a high-precision audit; all three let a caller reach ANOTHER tenant's
data with only an id/slug off the wire:

1. comms_app ChannelDetailView.get_queryset (channels.py) returned
   ``Channel.objects.filter(is_archived=False)`` with NO membership scoping, so
   any authenticated user could GET (read) and PATCH (rename / flip
   private->public / re-link the project FK) ANY channel by slug -- including
   private/direct channels. Fix: scope to the caller's ChannelMembership,
   mirroring the sibling ChannelListCreateView.get_queryset.

2. comms_app MessageListView.get_queryset (messages.py) filtered only by
   ``channel__slug`` -> returned the FULL message history of ANY channel by
   slug, private/DM included. Fix: require the caller to be a MEMBER
   (ChannelMembership.exists()) before returning messages, mirroring the
   membership check the write-path AgentSendMessageView.post enforces.

3. writer_app sections_config_view (metadata/sections.py) had ONLY
   ``@require_http_methods(["GET"])`` -- no auth/ownership gate -- yet
   WriterService(project_id, ...) resolves the project OWNER's writer_dir, so it
   leaked an arbitrary project's section structure to any caller (anonymous
   included). Fix: gate on ``user_can_access_project`` (owner/team/visitor),
   mirroring api_login_optional -- which cannot be applied as a decorator here
   because the route carries project_id as a query param, not a URL positional.

Each fix is one authorization check with no visible side effect, exactly the
kind of line a future refactor drops silently. This gate FAILS if any of the
three guards disappears from its OWN function body, so a regression is loud and
blocking.

The detector isolates the SPECIFIC function via ``ast`` (a sibling in the same
file already names ChannelMembership, so a whole-file scan would be vacuous),
then strips COMMENT and STRING tokens with ``tokenize`` (same technique as
test_idor_ownership / test_no_prefix_path_containment) so a guard named only in
a comment or docstring cannot keep the gate green -- "a review that reads code
is not a test that runs it". Pure static analysis: DB-free and mock-free (the
security-regression CI job has no Postgres and forbids unittest.mock).
"""
from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

_APPS = Path(__file__).resolve().parents[2] / "apps"
_COMMS_VIEWS = _APPS / "workspace" / "comms_app" / "views"
_CHANNELS = _COMMS_VIEWS / "channels.py"
_MESSAGES = _COMMS_VIEWS / "messages.py"
_SECTIONS = (
    _APPS
    / "workspace"
    / "writer_app"
    / "views"
    / "editor"
    / "api"
    / "metadata"
    / "sections.py"
)


def _live_code(source: str) -> str:
    """Return ``source`` with COMMENT and STRING tokens dropped, tokens re-joined.

    A guard named only in a comment or docstring must NOT satisfy the gate, so
    comments and strings are removed before matching. On an unparseable snippet
    we fall back to the raw text rather than silently passing (fail loud, no
    mask).
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    return "".join(
        t.string for t in toks if t.type not in (tokenize.COMMENT, tokenize.STRING)
    )


def _method_source(source: str, class_name: str, method_name: str) -> str:
    """Return the source of ``class_name.method_name`` only (isolated via ast).

    Scoping to the single method matters: a whole-file scan would be vacuous
    because a sibling in the same file (ChannelListCreateView / AgentSendMessage
    View) already names the guard token. Fail loud if the method is missing.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if (
                    isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and sub.name == method_name
                ):
                    seg = ast.get_source_segment(source, sub)
                    assert seg is not None, (
                        f"could not extract source of {class_name}.{method_name}"
                    )
                    return seg
    raise AssertionError(f"{class_name}.{method_name} not found in module source")


def _function_source(source: str, func_name: str) -> str:
    """Return the source of top-level function ``func_name`` only. Fail loud if absent."""
    tree = ast.parse(source)
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == func_name
        ):
            seg = ast.get_source_segment(source, node)
            assert seg is not None, f"could not extract source of {func_name}"
            return seg
    raise AssertionError(f"{func_name} not found in module source")


# --------------------------------------------------------------------------- #
# The three real gates                                                         #
# --------------------------------------------------------------------------- #
def test_channel_detail_get_queryset_scopes_by_membership():
    # Breakage caught: ChannelDetailView.get_queryset drops membership scoping,
    # re-exposing every channel (private/DM included) to GET/PATCH by slug.
    # Arrange
    method = _method_source(
        _CHANNELS.read_text(encoding="utf-8"), "ChannelDetailView", "get_queryset"
    )
    # Act
    code = _live_code(method)
    # Assert
    assert "ChannelMembership" in code, (
        "IDOR regression: ChannelDetailView.get_queryset no longer scopes to the "
        "caller's ChannelMembership. Without it any authenticated user can GET "
        "and PATCH ANY channel by slug (rename, flip private->public, re-link "
        "the project FK). Restore the membership scoping "
        "(mirror ChannelListCreateView.get_queryset; a comment does not count)."
    )


def test_message_list_get_queryset_scopes_by_membership():
    # Breakage caught: MessageListView.get_queryset filters by slug alone,
    # dumping the full history of any channel (private/DM included) to non-members.
    # Arrange
    method = _method_source(
        _MESSAGES.read_text(encoding="utf-8"), "MessageListView", "get_queryset"
    )
    # Act
    code = _live_code(method)
    # Assert
    assert "ChannelMembership" in code, (
        "IDOR regression: MessageListView.get_queryset returns messages by "
        "channel__slug with no membership check. Without verifying the caller is "
        "a member (ChannelMembership.exists()), any authenticated user can read "
        "the full history of ANY channel by slug. Restore the membership check "
        "(mirror AgentSendMessageView.post; a comment does not count)."
    )


def test_sections_config_view_keeps_ownership_gate():
    # Breakage caught: sections_config_view loses its access gate, leaking an
    # arbitrary project's section structure via ?project_id to any caller.
    # Arrange
    func = _function_source(
        _SECTIONS.read_text(encoding="utf-8"), "sections_config_view"
    )
    # Act
    code = _live_code(func)
    # Assert
    assert "user_can_access_project" in code, (
        "IDOR regression: sections_config_view no longer gates access to the "
        "project_id it reads from request.GET. WriterService resolves the "
        "project OWNER's writer_dir regardless of caller, so without the "
        "owner/team/visitor check (user_can_access_project) an unauthorized "
        "caller gets another tenant's section tree. Restore the gate "
        "(mirrors api_login_optional; a comment does not count)."
    )


# --------------------------------------------------------------------------- #
# Non-vacuity self-tests: prove the extractor + stripper actually flip red     #
# --------------------------------------------------------------------------- #
_SIBLING_MASK_SRC = (
    "class Safe:\n"
    "    def get_queryset(self):\n"
    "        return ChannelMembership.objects.filter(x=1)\n"
    "class Vuln:\n"
    "    def get_queryset(self):\n"
    "        return Channel.objects.all()\n"
)


def test_extractor_keeps_guard_in_the_guarded_sibling():
    # Non-vacuity: the guarded sibling's own body retains the guard token.
    # Arrange
    method = _method_source(_SIBLING_MASK_SRC, "Safe", "get_queryset")
    # Act
    code = _live_code(method)
    # Assert
    assert "ChannelMembership" in code


def test_extractor_drops_guard_from_a_vulnerable_sibling():
    # Non-vacuity: a whole-file scan would be vacuous (the sibling names the
    # token); scoping to the vulnerable method sees NO guard, so the gate flips.
    # Arrange
    method = _method_source(_SIBLING_MASK_SRC, "Vuln", "get_queryset")
    # Act
    code = _live_code(method)
    # Assert
    assert "ChannelMembership" not in code


def test_stripper_ignores_a_guard_named_only_in_a_comment():
    # Non-vacuity: a guard named only in a comment must NOT satisfy the gate.
    # Arrange
    src = (
        "def sections_config_view(request):\n"
        "    # user_can_access_project(request, project)\n"
        "    return 1\n"
    )
    # Act
    code = _live_code(_function_source(src, "sections_config_view"))
    # Assert
    assert "user_can_access_project" not in code


def test_stripper_ignores_a_guard_named_only_in_a_string():
    # Non-vacuity: a guard named only in a string literal must NOT satisfy the gate.
    # Arrange
    src = (
        "def sections_config_view(request):\n"
        '    doc = "call user_can_access_project here"\n'
        "    return doc\n"
    )
    # Act
    code = _live_code(_function_source(src, "sections_config_view"))
    # Assert
    assert "user_can_access_project" not in code


def test_stripper_keeps_a_live_guard_call():
    # Non-vacuity: a live guard call survives stripping, so the gate can see it.
    # Arrange
    src = (
        "def sections_config_view(request):\n"
        "    if not user_can_access_project(request, project):\n"
        "        return 403\n"
        "    return 1\n"
    )
    # Act
    code = _live_code(_function_source(src, "sections_config_view"))
    # Assert
    assert "user_can_access_project" in code


def test_method_source_raises_on_a_missing_class():
    # A renamed/removed target must raise, never pass vacuously.
    # Arrange
    src = _SIBLING_MASK_SRC
    # Act
    # Assert
    with pytest.raises(AssertionError):
        _method_source(src, "Nope", "get_queryset")


def test_function_source_raises_on_a_missing_function():
    # A renamed/removed target must raise, never pass vacuously.
    # Arrange
    src = _SIBLING_MASK_SRC
    # Act
    # Assert
    with pytest.raises(AssertionError):
        _function_source(src, "nope_func")
