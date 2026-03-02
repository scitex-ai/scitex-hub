/**
 * Git History Module
 * Provides visual commit history, diff viewer, and branch management
 */

interface GitCommit {
  sha: string;
  sha_short: string;
  message: string;
  author_name: string;
  author_email: string;
  date: string; // ISO format
  date_relative: string;
  parent_shas: string[];
  stats: {
    files_changed: number;
    insertions: number;
    deletions: number;
  };
}

interface GitStatus {
  branch: string;
  clean: boolean;
  files: {
    modified: string[];
    staged: string[];
    untracked: string[];
  };
}

interface GitDiff {
  files: Array<{
    path: string;
    change_type: "modified" | "added" | "deleted" | "renamed";
    diff: string;
    insertions: number;
    deletions: number;
  }>;
  stats: {
    files: number;
    insertions: number;
    deletions: number;
  };
}

interface GitBranch {
  name: string;
  is_current: boolean;
  commit_sha: string;
  commit_sha_short: string;
  commit_message: string;
  last_commit_date: string;
}

export class GitHistoryManager {
  private projectId: number;
  private timelineContainer: HTMLElement;
  private diffViewer: HTMLElement;
  private diffContent: HTMLElement;
  private branchSelect: HTMLSelectElement;
  private statusBadge: HTMLElement;
  private currentCommits: GitCommit[] = [];
  private selectedCommit: string | null = null;

  constructor(projectId: number) {
    this.projectId = projectId;

    // Get panel elements (no longer modal-specific)
    const timeline = document.getElementById("gitCommitTimeline");
    const diffViewer = document.getElementById("gitDiffViewer");
    const diffContent = document.getElementById("gitDiffContent");
    const branchSelect = document.getElementById("gitBranchSelect") as HTMLSelectElement;
    const statusBadge = document.getElementById("gitStatusBadge");

    if (!timeline || !diffViewer || !diffContent || !branchSelect || !statusBadge) {
      console.error("[GitHistory] Required elements not found");
      return;
    }

    this.timelineContainer = timeline;
    this.diffViewer = diffViewer;
    this.diffContent = diffContent;
    this.branchSelect = branchSelect;
    this.statusBadge = statusBadge;

    this.setupEventListeners();
    console.log("[GitHistory] Initialized with project:", projectId);
  }

  private setupEventListeners(): void {
    // Refresh button
    const refreshBtn = document.getElementById("gitRefreshBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.loadHistory());
    }

    // Close diff button
    const closeDiffBtn = document.getElementById("gitCloseDiffBtn");
    if (closeDiffBtn) {
      closeDiffBtn.addEventListener("click", () => this.closeDiff());
    }

    // Branch selector
    this.branchSelect.addEventListener("change", () => {
      this.loadHistory();
    });

    // Note: loadHistory(), loadBranches(), and loadStatus() are now called
    // directly from switchRightPanel() when the history view is activated
  }

  public async loadHistory(): Promise<void> {
    try {
      const branch = this.branchSelect.value;
      const response = await fetch(
        `/writer/api/project/${this.projectId}/git/history/?max_count=50&branch=${encodeURIComponent(branch)}`
      );

      if (!response.ok) throw new Error("Failed to load git history");

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load history");

      this.currentCommits = data.commits;
      this.renderTimeline();
    } catch (error) {
      console.error("[GitHistory] Error loading history:", error);
      this.timelineContainer.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-triangle me-2"></i>
          Failed to load commit history: ${error.message}
        </div>
      `;
    }
  }

  private renderTimeline(): void {
    if (this.currentCommits.length === 0) {
      this.timelineContainer.innerHTML = `
        <div class="git-empty-state">
          <div class="git-empty-icon">
            <i class="fas fa-code-branch"></i>
          </div>
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

    const html = this.currentCommits
      .map(
        (commit) => `
      <div class="git-commit-item" data-sha="${commit.sha}" onclick="window.gitHistoryManager.showCommitDiff('${commit.sha}')">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div class="git-commit-message">${this.escapeHtml(commit.message)}</div>
          <span class="git-commit-sha">${commit.sha_short}</span>
        </div>
        <div class="git-commit-author">
          <i class="fas fa-user me-1"></i>${this.escapeHtml(commit.author_name)}
          <span class="ms-3">
            <i class="far fa-clock me-1"></i>${commit.date_relative}
          </span>
        </div>
        <div class="git-commit-stats">
          <span class="stat">
            <i class="fas fa-file me-1"></i>${commit.stats.files_changed} file${commit.stats.files_changed !== 1 ? "s" : ""}
          </span>
          ${
            commit.stats.insertions > 0
              ? `<span class="stat additions">
            <i class="fas fa-plus"></i>+${commit.stats.insertions}
          </span>`
              : ""
          }
          ${
            commit.stats.deletions > 0
              ? `<span class="stat deletions">
            <i class="fas fa-minus"></i>-${commit.stats.deletions}
          </span>`
              : ""
          }
        </div>
      </div>
    `
      )
      .join("");

    this.timelineContainer.innerHTML = html;
  }

  public async showCommitDiff(commitSha: string): Promise<void> {
    try {
      // Update selected commit visuals
      this.selectedCommit = commitSha;
      this.timelineContainer.querySelectorAll(".git-commit-item").forEach((item) => {
        item.classList.remove("active");
      });
      const selectedItem = this.timelineContainer.querySelector(`[data-sha="${commitSha}"]`);
      if (selectedItem) {
        selectedItem.classList.add("active");
      }

      // Show loading in diff viewer
      this.diffViewer.style.display = "block";
      this.diffContent.innerHTML = `
        <div class="text-center text-muted py-4">
          <i class="fas fa-spinner fa-spin me-2"></i>Loading diff...
        </div>
      `;

      // Fetch diff
      const response = await fetch(
        `/writer/api/project/${this.projectId}/git/diff/?commit_sha=${encodeURIComponent(commitSha)}`
      );

      if (!response.ok) throw new Error("Failed to load diff");

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load diff");

      this.renderDiff(data.diff);
    } catch (error) {
      console.error("[GitHistory] Error loading diff:", error);
      this.diffContent.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-triangle me-2"></i>
          Failed to load diff: ${error.message}
        </div>
      `;
    }
  }

  private renderDiff(diff: GitDiff): void {
    if (diff.files.length === 0) {
      this.diffContent.innerHTML = `
        <div class="text-center text-muted py-3">
          <i class="fas fa-info-circle me-2"></i>
          No changes in this commit
        </div>
      `;
      return;
    }

    const html = diff.files
      .map(
        (file) => `
      <div class="git-diff-file">
        <div class="git-diff-file-header">
          <i class="fas fa-file-code me-2"></i>${this.escapeHtml(file.path)}
          <span class="badge bg-secondary ms-2">${file.change_type}</span>
          ${file.insertions > 0 ? `<span class="badge bg-success ms-1">+${file.insertions}</span>` : ""}
          ${file.deletions > 0 ? `<span class="badge bg-danger ms-1">-${file.deletions}</span>` : ""}
        </div>
        <div class="git-diff-lines">
          ${this.formatDiffLines(file.diff)}
        </div>
      </div>
    `
      )
      .join("");

    this.diffContent.innerHTML = html;
  }

  private formatDiffLines(diff: string): string {
    const lines = diff.split("\n");
    return lines
      .map((line) => {
        let className = "context";
        if (line.startsWith("+") && !line.startsWith("+++")) {
          className = "addition";
        } else if (line.startsWith("-") && !line.startsWith("---")) {
          className = "deletion";
        }
        return `<div class="git-diff-line ${className}">${this.escapeHtml(line)}</div>`;
      })
      .join("");
  }

  private closeDiff(): void {
    this.diffViewer.style.display = "none";
    this.selectedCommit = null;

    // Remove active state from all commits
    this.timelineContainer.querySelectorAll(".git-commit-item").forEach((item) => {
      item.classList.remove("active");
    });
  }

  public async loadBranches(): Promise<void> {
    try {
      const response = await fetch(`/writer/api/project/${this.projectId}/git/branches/`);

      if (!response.ok) throw new Error("Failed to load branches");

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load branches");

      const branches: GitBranch[] = data.branches;

      // Update branch select
      this.branchSelect.innerHTML = branches
        .map(
          (branch) => `
        <option value="${this.escapeHtml(branch.name)}" ${branch.is_current ? "selected" : ""}>
          ${this.escapeHtml(branch.name)}${branch.is_current ? " (current)" : ""}
        </option>
      `
        )
        .join("");
    } catch (error) {
      console.error("[GitHistory] Error loading branches:", error);
    }
  }

  public async loadStatus(): Promise<void> {
    try {
      const response = await fetch(`/writer/api/project/${this.projectId}/git/status/`);

      if (!response.ok) throw new Error("Failed to load status");

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load status");

      const status: GitStatus = data.status;

      // Update status badge
      if (status.clean) {
        this.statusBadge.className = "badge bg-success";
        this.statusBadge.innerHTML = '<i class="fas fa-check-circle me-1"></i>Working directory clean';
      } else {
        const totalChanges =
          status.files.modified.length + status.files.staged.length + status.files.untracked.length;
        this.statusBadge.className = "badge bg-warning";
        this.statusBadge.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${totalChanges} uncommitted change${totalChanges !== 1 ? "s" : ""}`;
      }
    } catch (error) {
      console.error("[GitHistory] Error loading status:", error);
    }
  }

  private async showCreateBranchDialog(): Promise<void> {
    const branchName = prompt("Enter new branch name:");
    if (!branchName) return;

    try {
      const response = await fetch(`/writer/api/project/${this.projectId}/git/branch/create/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCSRFToken(),
        },
        body: JSON.stringify({ branch_name: branchName }),
      });

      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to create branch");

      alert(`Branch '${branchName}' created successfully!`);
      await this.loadBranches();
    } catch (error) {
      console.error("[GitHistory] Error creating branch:", error);
      alert(`Failed to create branch: ${error.message}`);
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  private getCSRFToken(): string {
    const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }
}

// Export for global access
declare global {
  interface Window {
    gitHistoryManager: GitHistoryManager;
  }
}
