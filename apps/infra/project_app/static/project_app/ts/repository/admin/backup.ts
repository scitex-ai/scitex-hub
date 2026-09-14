/**
 * Project restore operations (orphaned repository -> new project)
 * @module repository/admin/backup
 */

import { PendingAction } from "./types";
import { createEl, DIALOG_NAME_STYLE, labelledParagraph } from "./dom";
import { t } from "./i18n";
import { showDialog, getCSRFToken, showError } from "./ui";

const PROJECT_NAME_INPUT_ID = "restore-project-name-input";

/**
 * Shows confirmation dialog for restoring an orphaned repository as a project
 */
export function confirmRestore(
  repositoryName: string,
  onExecute: () => void,
): PendingAction {
  const pendingAction: PendingAction = {
    type: "restore",
    name: repositoryName,
    projectName: repositoryName,
  };

  const dialogMessageEl = document.getElementById("dialog-message");

  if (dialogMessageEl) {
    const input = createEl("input", {
      style:
        "width: 100%; padding: 0.5rem; border: 1px solid var(--color-border-default); border-radius: 0.25rem; background: var(--color-canvas-subtle); color: var(--color-fg-default);",
      attrs: { type: "text", id: PROJECT_NAME_INPUT_ID },
    });
    input.value = repositoryName;

    dialogMessageEl.replaceChildren(
      createEl("p", {
        text: t(
          "dialog.restore.question",
          "Restore this orphaned repository by creating a new project?",
        ),
      }),
      createEl("p", { text: repositoryName, style: DIALOG_NAME_STYLE }),
      createEl("div", { style: "margin: 1rem 0;" }, [
        createEl("label", {
          text: t(
            "dialog.restore.name_label",
            "Project name for restored repository:",
          ),
          style: "display: block; margin-bottom: 0.5rem; font-weight: 500;",
          attrs: { for: PROJECT_NAME_INPUT_ID },
        }),
        input,
      ]),
      labelledParagraph(
        t("dialog.note_label", "Note:"),
        t(
          "dialog.restore.note",
          "This will create a new project linked to the existing Gitea repository and clone it to your local filesystem.",
        ),
      ),
    );
  }

  showDialog();

  // Focus input and setup enter key handler
  setTimeout(() => {
    const input = document.getElementById(
      PROJECT_NAME_INPUT_ID,
    ) as HTMLInputElement;
    if (input) {
      input.focus();
      input.addEventListener("keypress", (e: KeyboardEvent) => {
        if (e.key === "Enter") {
          onExecute();
        }
      });
    }
  }, 100);

  return pendingAction;
}

/**
 * Gets the project name from the restore input field
 */
export function getRestoreProjectName(defaultName: string): string {
  const input = document.getElementById(
    PROJECT_NAME_INPUT_ID,
  ) as HTMLInputElement;
  if (input) {
    return input.value.trim();
  }
  return defaultName;
}

/**
 * Restores an orphaned repository by creating a new project
 */
export async function restoreRepository(
  repositoryName: string,
  projectName: string,
  username: string,
  onSuccess: () => void,
): Promise<void> {
  console.log(
    "[Project Health] Restoring repository:",
    repositoryName,
    "as project:",
    projectName,
  );

  try {
    const response = await fetch(`/${username}/api/repository-restore/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        gitea_name: repositoryName,
        project_name: projectName,
      }),
    });

    const data = await response.json();

    if (data.success) {
      if (data.project_id) {
        const slugifiedName = projectName
          .toLowerCase()
          .replace(/\s+/g, "-")
          .replace(/[^\w\-]/g, "");

        setTimeout(() => {
          window.location.href = `/${username}/${slugifiedName}/`;
        }, 500);
      } else {
        setTimeout(() => onSuccess(), 500);
      }
    } else {
      console.error("[Project Health] API Error:", data);
      showError(
        data.message ||
          data.error ||
          t("error.restore", "Failed to restore project"),
      );
    }
  } catch (error) {
    console.error("[Project Health] Error:", error);
    showError(t("error.restore", "Failed to restore project"));
  }
}
