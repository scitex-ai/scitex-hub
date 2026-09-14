/**
 * Orphaned-repository cleanup operations
 * @module repository/admin/cleanup
 */

import { PendingAction } from "./types";
import { createEl, DIALOG_NAME_STYLE, labelledParagraph } from "./dom";
import { t } from "./i18n";
import { showDialog, getCSRFToken, showError } from "./ui";

/**
 * Shows confirmation dialog for deleting an orphaned Gitea repository
 */
export function confirmDelete(repositoryName: string): PendingAction {
  const pendingAction: PendingAction = {
    type: "delete",
    name: repositoryName,
  };

  const dialogMessageEl = document.getElementById("dialog-message");
  if (dialogMessageEl) {
    dialogMessageEl.replaceChildren(
      createEl("p", {
        text: t(
          "dialog.delete.question",
          "Are you sure you want to delete this orphaned repository?",
        ),
      }),
      createEl("p", { text: repositoryName, style: DIALOG_NAME_STYLE }),
      labelledParagraph(
        t("dialog.warning_label", "Warning:"),
        t(
          "dialog.delete.warning",
          "This action cannot be undone. The repository will be permanently deleted from Gitea.",
        ),
      ),
    );
  }

  showDialog();
  return pendingAction;
}

/**
 * Deletes an orphaned repository from Gitea
 */
export async function deleteRepository(
  repositoryName: string,
  username: string,
  onSuccess: () => void,
): Promise<void> {
  console.log("[Project Health] Deleting repository:", repositoryName);

  try {
    const response = await fetch(`/${username}/api/repository-cleanup/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ gitea_name: repositoryName }),
    });

    const data = await response.json();

    if (data.success) {
      setTimeout(() => onSuccess(), 500);
    } else {
      showError(
        data.message ||
          data.error ||
          t("error.delete", "Failed to delete repository"),
      );
    }
  } catch (error) {
    console.error("[Project Health] Error:", error);
    showError(t("error.delete", "Failed to delete repository"));
  }
}
