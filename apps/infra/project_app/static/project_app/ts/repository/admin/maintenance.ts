/**
 * Project Health maintenance tool
 * Manages project health monitoring, orphan detection, and sync operations
 * @module repository/admin/maintenance
 */

import { HealthData, PendingAction, FilterType } from "./types";
import { renderHealthStatus, renderIssues, applyFilter } from "./rendering";
import { showDialog, closeDialog, showError, getCSRFToken } from "./ui";
import {
  confirmRestore,
  restoreRepository,
  getRestoreProjectName,
} from "./backup";
import { confirmDelete, deleteRepository } from "./cleanup";
import { createEl, DIALOG_NAME_STYLE } from "./dom";
import { t } from "./i18n";

/**
 * Shows confirmation dialog for project sync
 */
function confirmSync(projectSlug: string): PendingAction {
  const pendingAction: PendingAction = {
    type: "sync",
    name: projectSlug,
  };

  const dialogMessageEl = document.getElementById("dialog-message");
  if (dialogMessageEl) {
    dialogMessageEl.replaceChildren(
      createEl("p", {
        text: t("dialog.sync.question", "Sync this project with Gitea?"),
      }),
      createEl("p", { text: projectSlug, style: DIALOG_NAME_STYLE }),
      createEl("p", {
        text: t(
          "dialog.sync.detail",
          "This will re-clone the repository from Gitea if the local directory is missing.",
        ),
      }),
    );
  }

  showDialog();
  return pendingAction;
}

/**
 * Syncs a repository with Gitea
 */
async function syncRepository(
  projectSlug: string,
  username: string,
  onSuccess: () => void,
): Promise<void> {
  console.log("[Project Health] Syncing repository:", projectSlug);

  try {
    const response = await fetch(`/${username}/api/repository-sync/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ project_slug: projectSlug }),
    });

    const data = await response.json();

    if (data.success) {
      setTimeout(() => onSuccess(), 500);
    } else {
      showError(
        data.message || data.error || t("error.sync", "Failed to sync project"),
      );
    }
  } catch (error) {
    console.error("[Project Health] Error:", error);
    showError(t("error.sync", "Failed to sync project"));
  }
}

/**
 * Main repository maintenance class
 */
class RepositoryMaintenance {
  private username: string = "";
  private healthData: HealthData | null = null;
  private pendingAction: PendingAction | null = null;
  private currentFilter: FilterType = "all";

  constructor() {
    this.init();
  }

  private init(): void {
    document.addEventListener("DOMContentLoaded", () => {
      console.log("[Project Health] Initializing");
      this.loadUsername();
      this.setupDialogBackdropClose();
      this.loadRepositoryHealth();
    });
  }

  private loadUsername(): void {
    const usernameEl = document.querySelector("[data-username]");
    if (usernameEl) {
      this.username = usernameEl.getAttribute("data-username") || "";
      console.log("[Project Health] Username:", this.username);
    } else {
      console.error("[Project Health] Username not found");
    }
  }

  private setupDialogBackdropClose(): void {
    const dialog = document.getElementById("confirmation-dialog");
    if (dialog) {
      dialog.addEventListener("click", (e: MouseEvent) => {
        if (e.target === dialog) {
          this.handleCloseDialog();
        }
      });
    }

    // Expose dialog functions to window
    (window as any).closeDialog = () => this.handleCloseDialog();
    (window as any).executeAction = () => this.executeAction();
    (window as any).confirmRestore = (name: string) =>
      this.handleConfirmRestore(name);
    (window as any).confirmDelete = (name: string) =>
      this.handleConfirmDelete(name);
    (window as any).confirmSync = (name: string) =>
      this.handleConfirmSync(name);
  }

  private async loadRepositoryHealth(): Promise<void> {
    console.log("[Project Health] Loading repository health");

    try {
      const response = await fetch(`/${this.username}/api/repository-health/`);
      const data: HealthData = await response.json();

      if (data.success) {
        this.healthData = data;
        this.renderHealth(data);
      } else {
        showError(
          data.error || t("error.load", "Failed to load project health"),
        );
      }
    } catch (error) {
      console.error("[Project Health] Error:", error);
      showError(t("error.connect", "Failed to connect to server"));
    }
  }

  private renderHealth(data: HealthData): void {
    renderHealthStatus(data, this.currentFilter);
    renderIssues(data);

    // Add click handlers to health cards
    const statusEl = document.getElementById("health-status");
    if (statusEl) {
      statusEl.querySelectorAll(".health-card").forEach((card) => {
        card.addEventListener("click", () => {
          const filter = card.getAttribute("data-filter") as FilterType;
          this.applyFilter(filter);
        });
      });
    }

    // Apply current filter
    applyFilter(this.currentFilter);
  }

  private applyFilter(filter: FilterType): void {
    this.currentFilter = filter;
    console.log("[Project Health] Applying filter:", filter);

    // Update health cards to show active state
    if (this.healthData) {
      renderHealthStatus(this.healthData, this.currentFilter);

      // Re-add click handlers after re-rendering
      const statusEl = document.getElementById("health-status");
      if (statusEl) {
        statusEl.querySelectorAll(".health-card").forEach((card) => {
          card.addEventListener("click", () => {
            const newFilter = card.getAttribute("data-filter") as FilterType;
            this.applyFilter(newFilter);
          });
        });
      }
    }

    // Filter the repository cards
    applyFilter(filter);
  }

  private handleConfirmRestore(repositoryName: string): void {
    this.pendingAction = confirmRestore(repositoryName, () =>
      this.executeAction(),
    );
  }

  private handleConfirmDelete(repositoryName: string): void {
    this.pendingAction = confirmDelete(repositoryName);
  }

  private handleConfirmSync(projectSlug: string): void {
    this.pendingAction = confirmSync(projectSlug);
  }

  private executeAction(): void {
    if (!this.pendingAction) {
      return;
    }

    const { type, name } = this.pendingAction;
    let projectName = this.pendingAction.projectName || name;

    if (type === "restore") {
      projectName = getRestoreProjectName(name);
    }

    this.handleCloseDialog();

    if (type === "restore") {
      restoreRepository(name, projectName, this.username, () =>
        this.loadRepositoryHealth(),
      );
    } else if (type === "delete") {
      deleteRepository(name, this.username, () => this.loadRepositoryHealth());
    } else if (type === "sync") {
      syncRepository(name, this.username, () => this.loadRepositoryHealth());
    }
  }

  private handleCloseDialog(): void {
    closeDialog();
    this.pendingAction = null;
  }
}

// Initialize on page load
export function initializeRepositoryMaintenance(): void {
  new RepositoryMaintenance();
}

// Auto-initialize
initializeRepositoryMaintenance();
