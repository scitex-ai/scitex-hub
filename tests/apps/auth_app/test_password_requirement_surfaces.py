#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which password policy each auth surface is allowed to state, and when.

TWO SEPARATE DEFECTS, both measured on the pages themselves.

(1) THE SIGN-IN PAGE STATED ACCOUNT-CREATION RULES. ``/auth/signin/`` and its
alias ``/auth/login/`` rendered a "Password Requirements:" panel listing
"At least 8 characters", "At least one uppercase letter" and so on, plus a
focus/typing handler that turned each line red or green as the visitor typed.
A returning user is entering the password they already have; the rules for
CREATING one are not merely useless there, they are misleading — a visitor
whose old password predates the policy reads five red crosses and concludes
their correct password is wrong. The panel was added as a "hint for
remembering registered password" (the comment that shipped with it) and no
requirement is enforced at sign-in at all.

(2) THE SIGN-UP PAGE PASSED JUDGEMENT BEFORE THE VISITOR HAD TYPED ANYTHING.
Its five requirement lines rendered as ``class="password-rule invalid"`` with
``fas fa-times`` — five red crosses on a form nobody has filled in yet, which
tells a first-time visitor they have already done something wrong. Judgement
belongs to the moment there is something to judge: neutral until input, then
valid/invalid.

WHAT "NEUTRAL" MEANS, MECHANICALLY, because "not red" is not a state a test can
pin: each rule carries the explicit ``neutral`` class, carries neither ``valid``
nor ``invalid``, and carries neither the check nor the cross icon. The class is
NOT decorative — ``test_the_neutral_state_is_actually_styled`` reads the
stylesheet the auth pages load and fails if nothing styles it, so removing the
CSS rule without removing the class cannot leave five invisible-but-present
"neutral" states behind.

THE LAST CLASS IS THE ONE THAT KEEPS EITHER FIX FROM BEING A DELETION.
``TestSignInStillAsksForAPassword`` asserts the sign-in form still asks for a
password and still offers the reset route: a template that dropped the password
field along with the requirements panel would satisfy every assertion above.

No mocks (project rule): the real URLconf, the real templates, the real views.
"""

import re
from html.parser import HTMLParser

import pytest
from django.urls import reverse

SIGNIN_URL = "/auth/signin/"
LOGIN_URL = "/auth/login/"
SIGNUP_URL = "/auth/signup/"

#: The five rules, verbatim as the template states them. Asserted by text and
#: not by id, because the ids are implementation detail; a visitor reading the
#: page is the party this contract is about.
REQUIREMENT_LABELS = (
    "At least 8 characters",
    "At least one lowercase letter",
    "At least one uppercase letter",
    "At least one number",
    "At least one special character",
)

RULE_IDS = ("rule-length", "rule-lowercase", "rule-uppercase", "rule-number", "rule-special")

#: The stylesheet the auth pages load (auth_app/templates/auth_app/auth_base.html).
AUTH_COMPONENT_CSS = "static/shared/css/components/forms/password.css"

_SIGNIN_DEFECT = (
    "signin.html (and /auth/login/, the same view and template) rendered the "
    "account-creation password rules, so a returning user's correct existing "
    "password was shown five red crosses."
)

SIGNUP_DEFECT = (
    "signup.html rendered its five password rules with class 'invalid' and a "
    "cross icon before the visitor had typed anything, judging an empty field."
)


class _PasswordRules(HTMLParser):
    """Every ``.password-rule`` element in the document, with its own icon.

    Collected from the SERVED html, not from the template source, so the
    assertions are about what a browser receives.
    """

    def __init__(self):
        super().__init__()
        self.rules = []  # [{"id": str, "classes": [str], "icon_classes": [str]}]
        self._open = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "div" and "password-rule" in classes and self._open is None:
            self._open = {
                "id": attrs.get("id") or "",
                "classes": classes,
                "icon_classes": [],
            }
        elif tag == "i" and self._open is not None:
            # Tokenised, like the rule's own classes: comparing a joined
            # "fas fa-times" against individual tokens is how the first draft of
            # this test passed while five red crosses were on the page.
            self._open["icon_classes"] = classes

    def handle_endtag(self, tag):
        if tag == "div" and self._open is not None:
            self.rules.append(self._open)
            self._open = None


def _rules(html):
    parser = _PasswordRules()
    parser.feed(html)
    return parser.rules


@pytest.fixture(params=[SIGNIN_URL, LOGIN_URL])
def signin_page(request, client):
    """Both URLs are the same view and the same template: two public doors."""
    return client.get(request.param).content.decode("utf-8")


@pytest.fixture
def signin_html(signin_page):
    return signin_page


@pytest.fixture
def signup_html(client):
    return client.get(SIGNUP_URL).content.decode("utf-8")


@pytest.mark.auth
@pytest.mark.guards(defect=_SIGNIN_DEFECT)
class TestSignInDoesNotStateAccountCreationRules:
    """A returning user's password is not created here, so its rules do not apply."""

    @pytest.mark.django_db
    def test_no_requirements_block_is_rendered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        present = "password-requirements" in html or "password-rules" in html
        # Assert
        assert present is False

    @pytest.mark.django_db
    def test_no_rule_is_rendered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        rules = _rules(html)
        # Assert
        assert rules == []

    @pytest.mark.django_db
    def test_no_rule_id_survives_without_its_panel(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        leftovers = [rule_id for rule_id in RULE_IDS if f'id="{rule_id}"' in html]
        # Assert
        assert leftovers == []

    @pytest.mark.django_db
    def test_no_creation_rule_text_is_rendered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        stated = [label for label in REQUIREMENT_LABELS if label in html]
        # Assert
        assert stated == []


@pytest.mark.auth
class TestSignInStillAsksForAPassword:
    """The fix is a removal, so it has to be pinned against over-removal."""

    @pytest.mark.django_db
    def test_the_password_field_is_still_rendered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        pattern = re.search(r'<input[^>]*type="password"[^>]*name="password"', html)
        # Assert
        assert pattern is not None

    @pytest.mark.django_db
    def test_the_username_field_is_still_rendered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        pattern = re.search(r'<input[^>]*name="username"', html)
        # Assert
        assert pattern is not None

    @pytest.mark.django_db
    def test_the_password_reset_route_is_still_offered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        href = reverse("auth_app:forgot_password")
        # Assert
        assert f'href="{href}"' in html

    @pytest.mark.django_db
    def test_the_remember_me_checkbox_is_still_rendered(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        pattern = re.search(r'type="checkbox"[^>]*name="remember_me"', html)
        # Assert
        assert pattern is not None


@pytest.mark.auth
@pytest.mark.guards(defect=SIGNUP_DEFECT)
class TestSignUpStatesItsRulesWithoutPrejudging:
    """The requirements stay — they just stop judging an empty field."""

    @pytest.mark.django_db
    def test_the_requirements_are_still_stated(self, signup_html):
        # Arrange: signup_html is the served sign-up page
        html = signup_html
        # Act
        stated = [label for label in REQUIREMENT_LABELS if label in html]
        # Assert
        assert stated == list(REQUIREMENT_LABELS)

    @pytest.mark.django_db
    def test_every_rule_is_rendered(self, signup_html):
        # Arrange: signup_html is the served sign-up page
        html = signup_html
        # Act
        ids = [rule["id"] for rule in _rules(html)]
        # Assert
        assert ids == list(RULE_IDS)

    @pytest.mark.django_db
    def test_no_rule_renders_as_valid_or_invalid(self, signup_html):
        # Arrange: signup_html is the served sign-up page, untouched
        html = signup_html
        # Act
        judged = [
            rule["id"]
            for rule in _rules(html)
            if "valid" in rule["classes"] or "invalid" in rule["classes"]
        ]
        # Assert
        assert judged == []

    @pytest.mark.django_db
    def test_every_rule_renders_neutral(self, signup_html):
        # Arrange: signup_html is the served sign-up page, untouched
        html = signup_html
        # Act
        not_neutral = [rule["id"] for rule in _rules(html) if "neutral" not in rule["classes"]]
        # Assert
        assert not_neutral == []

    @pytest.mark.django_db
    def test_no_rule_renders_a_verdict_icon(self, signup_html):
        # The icon is the half a sighted visitor reads first: a red cross on an
        # empty field is the defect, whatever the class list says.
        # Arrange: signup_html is the served sign-up page, untouched
        html = signup_html
        # Act
        verdicts = [
            rule["id"]
            for rule in _rules(html)
            if {"fa-check", "fa-times"} & set(rule["icon_classes"])
        ]
        # Assert
        assert verdicts == []


@pytest.mark.auth
class TestNoTemplateCommentLeaksOntoThePage:
    """A multi-line ``{# … #}`` is NOT a Django comment — it renders as text.

    Found the hard way while removing the sign-in panel: the explanatory note was
    written as a ``{# … #}`` spanning several lines, which Django's lexer does not
    recognise (``{# #}`` is single-line only), so the note shipped as visible
    text on the page — in every locale, English included, which is how the
    Japanese first-run test caught it. ``{% comment %}`` is the multi-line form.
    This is asserted on the SERVED page, so the next note that gets this wrong
    fails here instead of in a locale test about something else.
    """

    @pytest.mark.django_db
    def test_the_signin_page_carries_no_template_comment_syntax(self, signin_html):
        # Arrange: signin_html is the served sign-in page
        html = signin_html
        # Act
        leaks = [token for token in ("{#", "#}") if token in html]
        # Assert
        assert leaks == []

    @pytest.mark.django_db
    def test_the_signup_page_carries_no_template_comment_syntax(self, signup_html):
        # Arrange: signup_html is the served sign-up page
        html = signup_html
        # Act
        leaks = [token for token in ("{#", "#}") if token in html]
        # Assert
        assert leaks == []


@pytest.mark.auth
class TestTheNeutralStateIsReal:
    """A class nothing styles is not a state, it is a string."""

    def test_the_neutral_state_is_actually_styled(self):
        # Arrange: the stylesheet the auth pages load
        with open(AUTH_COMPONENT_CSS, encoding="utf-8") as handle:
            css = handle.read()
        # Act
        styled = re.search(r"\.password-rule\.neutral\s*\{", css)
        # Assert
        assert styled is not None

    def test_the_valid_and_invalid_states_are_still_styled(self):
        # Arrange: the stylesheet the auth pages load
        with open(AUTH_COMPONENT_CSS, encoding="utf-8") as handle:
            css = handle.read()
        # Act
        styled = [
            state
            for state in ("valid", "invalid")
            if re.search(rf"\.password-rule\.{state}\s*\{{", css)
        ]
        # Assert
        assert styled == ["valid", "invalid"]


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
