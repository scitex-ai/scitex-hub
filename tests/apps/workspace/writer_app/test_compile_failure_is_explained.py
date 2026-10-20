#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A failed compile must say why.

Measured in the real browser pass (Private Beta acceptance slice): with no LaTeX
toolchain in the environment, `POST /apps/writer/api/project/<id>/compile/`
answered

    200 {"success": false, "exit_code": 127,
         "stderr": "timeout: failed to run command 'latexmk': No such file or directory",
         "output_pdf": null, "errors": [], "warnings": []}

`CompilationResult` (the interface the client checks against,
static/writer_app/ts/types/api-responses.ts) declares `errors: string[]`, and the
product's own response validators treat a failure with an empty `errors` list as
an INVALID response. So the failure was real, silent in the machine-readable
half, and indistinguishable from a broken manuscript.

The fix adds a reason only where one is missing; these tests pin that it does not
touch a result that already explains itself, and does not invent one for success.
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.workspace.writer_app.views.editor.api.compilation import (
    _explain_compile_failure,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret
TOOLCHAIN_STDERR = (
    "timeout: failed to run command \u2018latexmk\u2019: No such file or directory\n"
)


class CompileFailureExplainsItselfTest(TestCase):
    """The pure decision, so it holds on a machine that HAS a toolchain too."""

    def test_a_missing_toolchain_is_named_as_such(self):
        # Arrange: the exact shape measured in the browser pass.
        result = {
            "success": False,
            "exit_code": 127,
            "stdout": "",
            "stderr": TOOLCHAIN_STDERR,
            "output_pdf": None,
            "errors": [],
            "warnings": [],
        }
        # Act
        explained = _explain_compile_failure(result)
        # Assert
        assert len(explained["errors"]) == 1, explained
        assert "toolchain unavailable" in explained["errors"][0], explained
        assert "latexmk" in explained["errors"][0], explained

    def test_a_not_executable_toolchain_counts_too(self):
        # Arrange: 126 is "found but not executable", the sibling of 127.
        result = {"success": False, "exit_code": 126, "stderr": "Permission denied", "errors": []}
        # Act
        explained = _explain_compile_failure(result)
        # Assert
        assert "toolchain unavailable" in explained["errors"][0], explained

    def test_a_latex_error_keeps_its_own_message(self):
        # Arrange: the compile DID run and the manuscript is what failed.
        result = {
            "success": False,
            "exit_code": 1,
            "stderr": "! Undefined control sequence.",
            "errors": [],
        }
        # Act
        explained = _explain_compile_failure(result)
        # Assert
        assert explained["errors"] == ["! Undefined control sequence."], explained

    def test_a_silent_failure_still_gets_a_reason(self):
        # Arrange
        result = {"success": False, "exit_code": 12, "stderr": "", "errors": []}
        # Act
        explained = _explain_compile_failure(result)
        # Assert
        assert explained["errors"] == ["compilation failed with exit code 12"], explained

    def test_a_failure_that_already_explains_itself_is_untouched(self):
        # Arrange
        result = {"success": False, "exit_code": 1, "stderr": "x", "errors": ["already here"]}
        # Act / Assert: identity, not equality — nothing was rebuilt.
        assert _explain_compile_failure(result) is result
        assert result["errors"] == ["already here"]

    def test_a_successful_compile_is_untouched(self):
        # Arrange
        result = {"success": True, "exit_code": 0, "stderr": "", "errors": [], "output_pdf": "/x.pdf"}
        # Act
        explained = _explain_compile_failure(result)
        # Assert
        assert explained["errors"] == [], explained
        assert explained["output_pdf"] == "/x.pdf"


class CompileEndpointContractTest(TestCase):
    """The endpoint's failure must satisfy the interface the client declares."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="compile-contract-owner", password=PASSWORD)
        cls.project = Project.objects.create(
            slug="compile-contract", owner=cls.owner, name="compile-contract", visibility="private"
        )
        get_project_filesystem_manager(cls.owner).create_project_directory(
            cls.project, use_template=False
        )

    def test_a_failed_compile_is_not_a_bare_failure(self):
        # Arrange
        client = Client()
        client.login(username="compile-contract-owner", password=PASSWORD)
        body = json.dumps({"content": "\\section{A}\ntext\n", "doc_type": "manuscript"})
        # Act
        response = client.post(
            f"/apps/writer/api/project/{self.project.pk}/compile/",
            data=body, content_type="application/json",
        )
        payload = json.loads(response.content)
        # Assert: on a machine WITH LaTeX this may succeed; either way the response
        # must never be a failure that explains nothing.
        assert response.status_code < 500, response.content
        if payload.get("success") is False:
            assert payload.get("errors"), payload
            assert isinstance(payload["errors"][0], str), payload


# EOF
