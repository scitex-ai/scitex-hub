/**
 * Git History Module — Thin orchestrator
 * Delegates diff rendering to GitDiffViewer (which uses MonacoDiffEditor).
 * Handles commit timeline, branch management, and status display.
 */

import { GitDiffViewer } from "./_git-history/diff-viewer";
import type {
  GitBranch,
  GitCommit,
  GitDiff,
  GitStatus,
} from "./_git-history/types";
import { getCsrfToken } from "../shared/utils";

export type {
  GitCommit,
  GitDiff,
  GitDiffFile,
  GitBranch,
  GitStatus,
} from "./_git-history/types";

export class GitHistoryManager {
  private projectId: number;
  private timelineContainer!: HTMLElement;
  private diffViewer!: HTMLElement;
  private diffContent!: HTMLElement;
  private branchSelect!: HTMLSelectElement;
  private statusBadge!: HTMLElement;
  private commitForm!: HTMLElement;
  private commitMessageInput!: HTMLInputElement;
  private commitBtn!: HTMLButtonElement;
  private commitFeedback!: HTMLElement;
  private currentCommits: GitCommit[] = [];
  private selectedCommit: string | null = null;
  private gitDiffViewer: GitDiffViewer | null = null;

  constructor(projectId: number) {
    this.projectId = projectId;

    const timeline = document.getElementById("gitCommitTimeline");
    const diffViewer = document.getElementById("gitDiffViewer");
    const diffContent = document.getElementById("gitDiffContent");
    const branchSelect = document.getElementById(
      "gitBranchSelect",
    ) as HTMLSelectElement;
    const statusBadge = document.getElementById("gitStatusBadge");

    if (
      !timeline ||
      !diffViewer ||
      !diffContent ||
      !branchSelect ||
      !statusBadge
    ) {
      console.error("[GitHistory] Required elements not found");
      return;
    }

    this.timelineContainer = timeline;
    this.diffViewer = diffViewer;
    this.diffContent = diffContent;
    this.branchSelect = branchSelect;
    this.statusBadge = statusBadge;

    const commitForm = document.getElementById("gitCommitForm");
    const commitMsg = document.getElementById(
      "gitCommitMessage",
    ) as HTMLInputElement;
    const commitBtn = document.getElementById(
      "gitCommitBtn",
    ) as HTMLButtonElement;
    const commitFeedback = document.getElementById("gitCommitFeedback");
    if (commitForm && commitMsg && commitBtn && commitFeedback) {
      this.commitForm = commitForm;
      this.commitMessageInput = commitMsg;
      this.commitBtn = commitBtn;
      this.commitFeedback = commitFeedback;
    }

    this.setupEventListeners();
    console.log("[GitHistory] Initialized with project:", projectId);
  }

  private setupEventListeners(): void {
    const refreshBtn = document.getElementById("gitRefreshBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.loadHistory());
    }

    const closeDiffBtn = document.getElementById("gitCloseDiffBtn");
    if (closeDiffBtn) {
      closeDiffBtn.addEventListener("click", () => this.closeDiff());
    }

    this.branchSelect.addEventListener("change", () => {
      this.loadHistory();
    });

    if (this.commitBtn) {
      this.commitBtn.addEventListener("click", () => {
        const msg = this.commitMessageInput.value.trim();
        if (msg) {
          this.createCommit(msg);
        }
      });
    }

    if (this.commitMessageInput) {
      this.commitMessageInput.addEventListener(
        "keydown",
        (e: KeyboardEvent) => {
          if (e.key === "Enter") {
            const msg = this.commitMessageInput.value.trim();
            if (msg) {
              this.createCommit(msg);
            }
          }
        },
      );
    }
  }

  // ── Data loading ───────────────────────────────────────────────────

  public async loadHistory(): Promise<void> {
    try {
      const branch = this.branchSelect.value;
      const response = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/history/?max_count=50&branch=${encodeURIComponent(branch)}`,
      );
      if (!response.ok) throw new Error("Failed to load git history");

      const data = await response.json();
      if (!data.success)
        throw new Error(data.error || "Failed to load history");

      this.currentCommits = data.commits;
      this.renderTimeline();
    } catch (error: any) {
      console.error("[GitHistory] Error loading history:", error);
      this.timelineContainer.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-triangle me-2"></i>
          Failed to load commit history: ${error.message}
        </div>
      `;
    }
  }

  public async loadBranches(): Promise<void> {
    try {
      const response = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/branches/`,
      );
      if (!response.ok) throw new Error("Failed to load branches");

      const data = await response.json();
      if (!data.success)
        throw new Error(data.error || "Failed to load branches");

      const branches: GitBranch[] = data.branches;
      this.branchSelect.innerHTML = branches
        .map(
          (branch) =>
            `<option value="${this.escapeHtml(branch.name)}" ${branch.is_current ? "selected" : ""}>` +
            `${this.escapeHtml(branch.name)}${branch.is_current ? " (current)" : ""}` +
            `</option>`,
        )
        .join("");
    } catch (error) {
      console.error("[GitHistory] Error loading branches:", error);
    }
  }

  public async loadStatus(): Promise<void> {
    try {
      const response = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/status/`,
      );
      if (!response.ok) throw new Error("Failed to load status");

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load status");

      const status: GitStatus = data.status;
      if (status.clean) {
        this.statusBadge.className = "badge bg-success";
        this.statusBadge.innerHTML =
          '<i class="fas fa-check-circle me-1"></i>Working directory clean';
      } else {
        const total =
          status.files.modified.length +
          status.files.staged.length +
          status.files.untracked.length;
        this.statusBadge.className = "badge bg-warning";
        this.statusBadge.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${total} uncommitted change${total !== 1 ? "s" : ""}`;
      }

      if (this.commitForm) {
        this.commitForm.style.display = status.clean ? "none" : "block";
      }
    } catch (error) {
      console.error("[GitHistory] Error loading status:", error);
    }
  }

  // ── Commit creation ───────────────────────────────────────────────

  public async createCommit(message: string): Promise<void> {
    this.commitBtn.disabled = true;
    this.commitFeedback.style.display = "none";

    try {
      const response = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/commit/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({ message }),
        },
      );

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || "Commit failed");
      }

      this.commitMessageInput.value = "";
      this.commitFeedback.style.display = "block";
      this.commitFeedback.className = "git-commit-feedback text-success";
      this.commitFeedback.textContent = `Committed ${data.commit_sha_short}`;

      await Promise.all([this.loadHistory(), this.loadStatus()]);
    } catch (error: any) {
      console.error("[GitHistory] Commit error:", error);
      this.commitFeedback.style.display = "block";
      this.commitFeedback.className = "git-commit-feedback text-danger";
      this.commitFeedback.textContent = error.message;
    } finally {
      this.commitBtn.disabled = false;
    }
  }

  // ── Timeline rendering ─────────────────────────────────────────────

  private renderTimeline(): void {
    if (this.currentCommits.length === 0) {
      this.timelineContainer.innerHTML = `
        <div class="git-empty-state">
          <div class="git-empty-icon"><i class="fas fa-code-branch"></i></div>
          <h6 class="git-empty-title">No commits yet</h6>
          <p class="git-empty-description">
            Start tracking your document changes by making your first commit
          </p>
          <div class="git-empty-hint">
            <i class="fas fa-lightbulb me-1"></i>
            Tip: Your changes are automatically committed when you save
          </div>
        </div>
      `;
      return;
    }

    this.timelineContainer.innerHTML = this.currentCommits
      .map((c) => this.renderCommitItem(c))
      .join("");
  }

  private renderCommitItem(commit: GitCommit): string {
    const ins =
      commit.stats.insertions > 0
        ? `<span class="stat additions"><i class="fas fa-plus"></i>+${commit.stats.insertions}</span>`
        : "";
    const del =
      commit.stats.deletions > 0
        ? `<span class="stat deletions"><i class="fas fa-minus"></i>-${commit.stats.deletions}</span>`
        : "";

    return `
      <div class="git-commit-item" data-sha="${commit.sha}"
           onclick="window.gitHistoryManager.showCommitDiff('${commit.sha}')">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div class="git-commit-message">${this.escapeHtml(commit.message)}</div>
          <span class="git-commit-sha">${commit.sha_short}</span>
        </div>
        <div class="git-commit-author">
          <i class="fas fa-user me-1"></i>${this.escapeHtml(commit.author_name)}
          <span class="ms-3"><i class="far fa-clock me-1"></i>${commit.date_relative}</span>
        </div>
        <div class="git-commit-stats">
          <span class="stat">
            <i class="fas fa-file me-1"></i>${commit.stats.files_changed} file${commit.stats.files_changed !== 1 ? "s" : ""}
          </span>
          ${ins}${del}
        </div>
      </div>`;
  }

  // ── Diff display (delegates to GitDiffViewer) ──────────────────────

  public async showCommitDiff(commitSha: string): Promise<void> {
    try {
      this.selectedCommit = commitSha;
      this.timelineContainer
        .querySelectorAll(".git-commit-item")
        .forEach((el) => {
          el.classList.remove("active");
        });
      this.timelineContainer
        .querySelector(`[data-sha="${commitSha}"]`)
        ?.classList.add("active");

      this.diffViewer.style.display = "block";
      this.diffContent.innerHTML = `
        <div class="text-center text-muted py-4">
          <i class="fas fa-spinner fa-spin me-2"></i>Loading diff...
        </div>
      `;

      const response = await fetch(
        `/apps/writer/api/project/${this.projectId}/git/diff/?commit_sha=${encodeURIComponent(commitSha)}`,
      );
      if (!response.ok) throw new Error("Failed to load diff");

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load diff");

      // Destroy previous viewer before creating a new one
      if (this.gitDiffViewer) {
        this.gitDiffViewer.destroy();
      }
      this.gitDiffViewer = new GitDiffViewer(this.diffContent);
      this.gitDiffViewer.renderDiff(data.diff as GitDiff);
    } catch (error: any) {
      console.error("[GitHistory] Error loading diff:", error);
      this.diffContent.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-triangle me-2"></i>
          Failed to load diff: ${error.message}
        </div>
      `;
    }
  }

  private closeDiff(): void {
    if (this.gitDiffViewer) {
      this.gitDiffViewer.destroy();
      this.gitDiffViewer = null;
    }
    this.diffViewer.style.display = "none";
    this.selectedCommit = null;
    this.timelineContainer
      .querySelectorAll(".git-commit-item")
      .forEach((el) => {
        el.classList.remove("active");
      });
  }

  // ── Utilities ──────────────────────────────────────────────────────

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// Export for global access from onclick handlers
declare global {
  interface Window {
    gitHistoryManager: GitHistoryManager;
  }
}
