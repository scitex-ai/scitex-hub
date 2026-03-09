/**
 * Repository cleanup operations
 * @module repository/admin/cleanup
 */

import { PendingAction } from "./types";
import { escapeHtml } from "./rendering";
import { showDialog, getCSRFToken, showError } from "./ui";

/**
 * Shows confirmation dialog for repository deletion
 */
export function confirmDelete(repositoryName: string): PendingAction {
  const pendingAction: PendingAction = {
    type: "delete",
    name: repositoryName,
  };

  const dialogMessageEl = document.getElementById("dialog-message");
  if (dialogMessageEl) {
    dialogMessageEl.innerHTML = `
            <p>Are you sure you want to delete this orphaned repository?</p>
            <p style="margin: 1rem 0; font-family: monospace; background: var(--color-canvas-subtle); padding: 0.5rem; border-radius: 0.25rem; word-break: break-all;">
                ${escapeHtml(repositoryName)}
            </p>
            <p><strong>Warning:</strong> This action cannot be undone. The repository will be permanently deleted from Gitea.</p>
        `;
  }

  showDialog();
  return pendingAction;
}

/**
 * Deletes a repository from Gitea
 */
export async function deleteRepository(
  repositoryName: string,
  username: string,
  onSuccess: () => void,
): Promise<void> {
  console.log("[Repository Maintenance] Deleting repository:", repositoryName);

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
      showError(data.message || data.error);
    }
  } catch (error) {
    console.error("[Repository Maintenance] Error:", error);
    showError("Failed to delete repository");
  }
}
