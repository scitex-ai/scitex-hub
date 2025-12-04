/**
 * Issue Detail Page
 * Functions for closing and reopening issues
 */

import { getCsrfToken } from "../utils/csrf.ts";

console.log(
  "[DEBUG] apps/project_app/static/project_app/ts/issues/detail.ts loaded",
);

(function () {
  "use strict";

  interface IssueResponse {
    success: boolean;
    error?: string;
  }

  async function closeIssue(): Promise<void> {
    if (!confirm("Are you sure you want to close this issue?")) return;

    const closeUrl = document.body.dataset.issueCloseUrl;
    if (!closeUrl) {
      console.error("Issue close URL not found");
      return;
    }

    const csrfToken = getCsrfToken();
    if (!csrfToken) {
      console.error("CSRF token not found");
      return;
    }

    try {
      const response = await fetch(closeUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      });

      const data = (await response.json()) as IssueResponse;
      if (data.success) {
        location.reload();
      } else {
        alert(data.error || "Failed to close issue");
      }
    } catch (error) {
      console.error("Error closing issue:", error);
      alert("Failed to close issue");
    }
  }

  async function reopenIssue(): Promise<void> {
    const reopenUrl = document.body.dataset.issueReopenUrl;
    if (!reopenUrl) {
      console.error("Issue reopen URL not found");
      return;
    }

    const csrfToken = getCsrfToken();
    if (!csrfToken) {
      console.error("CSRF token not found");
      return;
    }

    try {
      const response = await fetch(reopenUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      });

      const data = (await response.json()) as IssueResponse;
      if (data.success) {
        location.reload();
      } else {
        alert(data.error || "Failed to reopen issue");
      }
    } catch (error) {
      console.error("Error reopening issue:", error);
      alert("Failed to reopen issue");
    }
  }

  // Export functions to window
  (window as any).closeIssue = closeIssue;
  (window as any).reopenIssue = reopenIssue;
})();
