<!-- ---
!-- Timestamp: 2025-12-08 05:33:43
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/tests/e2e/README.md
!-- --- -->

# E2E Tests

## Requests
1. No stealth mode (headed) for e2e tests
2. Use ~/proj/scitex-code/src/scitex/browser to show what is happening ongoingly with "message and visual feedback in the browser"
   e.g., [1/4] Testing XXX...
   e.g., [2/4] Clicking XXX...
   e.g., [3/4] Dragging XXX...
   e.g., [4/4] Checcking XXX is YYY...
3. Add click effects, cursor move effects
   4. Update the scitex-code side if reusable update available
4. Keep each test file small
5. Format each test file with pytest
6. Problems are not "unlucky situation". Similar situations will be repeated in the future. Thus, seriously consider how to prevent, how to detect in an systematic manner.
7. Logics should be implemented in ~/scitex-code/src/scitex/{browser,capture} and so on for reuse
8. Use 8 chrome instances in parallel
9. Do not wait for long time - You can run tests in background and check results periodically.

pytest tests/e2e/shared/panel_resizer/

## auth/ (35 tests)
- test_login.py (12 tests)
- test_signup.py (11 tests)
- test_password_reset.py (12 tests)

## project/ (12 tests)
- test_project_crud.py (7 tests)
- test_file_tree.py (5 tests)

## scholar/ (5 tests)
- test_bibtex.py (5 tests)

## writer/ (planned)
- test_editor.py
- test_compilation.py

## code/ (planned)
- test_notebook.py
- test_execution.py

## vis/ (planned)
- test_graph_editor.py

<!-- EOF -->