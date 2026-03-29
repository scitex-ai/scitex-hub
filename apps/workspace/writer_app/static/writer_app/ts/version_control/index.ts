/**
 * Version control dashboard page functionality.
 * Wires up commit list, branch switching, and diff viewing.
 * Corresponds to: templates/writer_app/version_control/index.html
 */

class VersionControlPage {
  private container: HTMLElement | null;
  private projectId: string | null;
  private diffViewer: HTMLElement | null;
  private diffContent: HTMLElement | null;

  constructor() {
    this.container = document.querySelector(".version-control-container");
    this.projectId = this.container?.dataset.projectId ?? null;
    this.diffViewer = document.getElementById("diff-viewer");
    this.diffContent = document.getElementById("diff-content");
    this.init();
  }

  private init(): void {
    if (!this.projectId) {
      console.warn("[VersionControl] No project ID found");
      return;
    }
    this.setupCommitClicks();
    this.setupBranchClicks();
    this.setupButtons();
  }

  private setupCommitClicks(): void {
    const commitItems = document.querySelectorAll<HTMLElement>(".commit-item[data-sha]");
    commitItems.forEach((item) => {
      item.addEventListener("click", () => {
        const sha = item.dataset.sha;
        if (sha) this.showDiff(sha);
      });
    });
  }

  private setupBranchClicks(): void {
    const branchItems = document.querySelectorAll<HTMLElement>(".branch-item[data-branch]");
    branchItems.forEach((item) => {
      item.addEventListener("click", () => {
        const branch = item.dataset.branch;
        if (branch) this.switchBranch(branch);
      });
    });
  }

  private setupButtons(): void {
    document.getElementById("btn-commit")?.addEventListener("click", () => {
      const modal = document.getElementById("create-version-modal");
      if (modal) modal.style.display = "block";
    });

    document.getElementById("btn-create-branch")?.addEventListener("click", () => {
      const modal = document.getElementById("create-branch-modal");
      if (modal) modal.style.display = "block";
    });

    // Close buttons for modals
    document.querySelectorAll(".close").forEach((btn) => {
      btn.addEventListener("click", () => {
        const modal = btn.closest(".modal");
        if (modal instanceof HTMLElement) modal.style.display = "none";
      });
    });
  }

  private async showDiff(commitSha: string): Promise<void> {
    if (!this.diffViewer || !this.diffContent) return;

    this.diffViewer.classList.remove("hidden");
    this.diffContent.innerHTML = '<div class="loading">Loading diff...</div>';

    try {
      const resp = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/diff/?commit_sha=${commitSha}`
      );
      const data = await resp.json();

      if (data.success && data.diff?.files) {
        this.renderDiff(data.diff.files);
      } else {
        this.diffContent.innerHTML = '<div class="empty-state-message">No changes in this commit</div>';
      }
    } catch (err) {
      console.error("[VersionControl] Diff fetch error:", err);
      this.diffContent.innerHTML = '<div class="empty-state-message">Error loading diff</div>';
    }
  }

  private renderDiff(files: Array<{ path: string; status: string; insertions: number; deletions: number; content_original?: string; content_modified?: string }>): void {
    if (!this.diffContent) return;

    const html = files
      .map(
        (file) => `
      <div class="diff-file">
        <div class="diff-file-header">
          <span class="diff-file-name">${this.escapeHtml(file.path)}</span>
          <span class="diff-file-status ${file.status}">${file.status}</span>
          <span class="commit-stats">
            <span class="stat-add">+${file.insertions}</span>
            <span class="stat-del">-${file.deletions}</span>
          </span>
        </div>
      </div>
    `
      )
      .join("");

    this.diffContent.innerHTML = html || '<div class="empty-state-message">No file changes</div>';
  }

  private async switchBranch(branchName: string): Promise<void> {
    try {
      const csrfToken = this.getCsrfToken();
      const resp = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/branch/switch/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({ branch: branchName }),
        }
      );
      const data = await resp.json();
      if (data.success) {
        window.location.reload();
      } else {
        console.error("[VersionControl] Branch switch failed:", data.error);
      }
    } catch (err) {
      console.error("[VersionControl] Branch switch error:", err);
    }
  }

  private getCsrfToken(): string {
    const cookie = document.cookie.split(";").find((c) => c.trim().startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new VersionControlPage();
});
