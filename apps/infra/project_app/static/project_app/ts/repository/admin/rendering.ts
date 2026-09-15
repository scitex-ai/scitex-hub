/**
 * Rendering functions for the Project Health UI
 * @module repository/admin/rendering
 *
 * Everything is built with DOM nodes + textContent: user-visible strings come
 * from the i18n catalog and names come from the API, so neither may be parsed
 * as HTML.
 */

import { HealthData, RepositoryIssue, FilterType } from "./types";
import { createEl } from "./dom";
import { t } from "./i18n";

/**
 * Escapes HTML special characters
 */
export function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

function healthCard(
  filter: FilterType,
  extraClass: string,
  currentFilter: FilterType,
  value: number,
  label: string,
  title: string,
): HTMLElement {
  const classes = ["health-card", extraClass];
  if (currentFilter === filter) {
    classes.push("active");
  }
  return createEl(
    "div",
    {
      className: classes.filter(Boolean).join(" "),
      attrs: { "data-filter": filter, title },
    },
    [
      createEl("div", { className: "health-card-value", text: String(value) }),
      createEl("div", { className: "health-card-label", text: label }),
    ],
  );
}

/**
 * Renders the health status cards
 */
export function renderHealthStatus(
  data: HealthData,
  currentFilter: FilterType,
): void {
  const stats = data.stats;
  const statusEl = document.getElementById("health-status");
  if (!statusEl) {
    return;
  }
  statusEl.replaceChildren(
    healthCard(
      "healthy",
      "success",
      currentFilter,
      stats.healthy_count,
      t("card.healthy.label", "Healthy"),
      t("card.healthy.title", "Click to show only healthy projects"),
    ),
    healthCard(
      "warnings",
      "warning",
      currentFilter,
      stats.warnings,
      t("card.warnings.label", "Warnings"),
      t("card.warnings.title", "Click to show only warnings"),
    ),
    healthCard(
      "critical",
      stats.critical_issues > 0 ? "critical" : "",
      currentFilter,
      stats.critical_issues,
      t("card.critical.label", "Critical"),
      t("card.critical.title", "Click to show only critical issues"),
    ),
    healthCard(
      "all",
      "",
      currentFilter,
      stats.total_django_projects,
      t("card.total.label", "Total Projects"),
      t("card.total.title", "Click to show all projects"),
    ),
  );
}

const PRESENT = "✓ ";
const ABSENT = "✗ ";

interface IssueColumns {
  local: string;
  project: string;
  repository: string;
  typeLabel: string;
  message: string;
}

function issueColumns(issue: RepositoryIssue): IssueColumns {
  const local = t("value.local", "Local");
  const project = t("value.project", "Project");
  const repository = t("value.repository", "Repository");
  const missing = t("value.missing", "Missing");
  const columns: IssueColumns = {
    local: "—",
    project: "—",
    repository: "—",
    typeLabel: "",
    message: issue.message,
  };

  if (issue.issue_type === "healthy") {
    columns.local = PRESENT + local;
    columns.project = PRESENT + project;
    columns.repository = PRESENT + repository;
    columns.typeLabel = t("type.healthy", "In sync");
    columns.message = t("message.healthy", "Project healthy and in sync");
  } else if (issue.issue_type === "orphaned_in_gitea") {
    columns.repository = PRESENT + repository;
    columns.typeLabel = t("type.orphaned_in_gitea", "Orphaned in Gitea");
    columns.message = t(
      "message.orphaned_in_gitea",
      "Repository exists in Gitea but no project found",
    );
  } else if (issue.issue_type === "missing_in_gitea") {
    columns.local = "?";
    columns.project = PRESENT + project;
    columns.repository = ABSENT + missing;
    columns.typeLabel = t("type.missing_in_gitea", "Repository missing");
    columns.message = t(
      "message.missing_in_gitea",
      "Project exists but its Gitea repository was not found",
    );
  } else if (issue.issue_type === "missing_directory") {
    columns.local = ABSENT + missing;
    columns.project = PRESENT + project;
    columns.repository = PRESENT + repository;
    columns.typeLabel = t("type.missing_directory", "Local directory missing");
    const text = t("message.missing_directory", "Local git directory missing");
    columns.message = issue.detail ? `${text}: ${issue.detail}` : text;
  }
  return columns;
}

function actionButton(
  label: string,
  handlerName: "confirmRestore" | "confirmSync",
  name: string,
): HTMLButtonElement {
  const button = createEl("button", {
    className: "issue-button sync",
    text: label,
    attrs: { type: "button" },
  });
  button.addEventListener("click", () => {
    const handler = (window as any)[handlerName];
    if (typeof handler === "function") {
      handler(name);
    }
  });
  return button;
}

function statusColumn(label: string, value: string): HTMLElement {
  return createEl("div", { className: "status-column" }, [
    createEl("div", { className: "status-label", text: label }),
    createEl("div", { className: "status-value", text: value }),
  ]);
}

/**
 * Renders a single project issue card
 */
export function renderIssue(issue: RepositoryIssue): HTMLElement {
  const icon = issue.is_healthy ? "✓" : issue.is_critical ? "✗" : "⚠";
  const status = issue.is_healthy
    ? "healthy"
    : issue.is_critical
      ? "critical"
      : "warning";
  const name =
    issue.project_slug ||
    issue.gitea_name ||
    t("issue.unknown_name", "Unknown");
  const columns = issueColumns(issue);

  const actions = createEl("div", { className: "issue-actions" });
  if (issue.issue_type === "orphaned_in_gitea") {
    actions.appendChild(
      actionButton(
        "↺ " + t("action.restore", "Restore Project"),
        "confirmRestore",
        name,
      ),
    );
  } else if (
    issue.issue_type === "missing_in_gitea" ||
    issue.issue_type === "missing_directory"
  ) {
    actions.appendChild(
      actionButton(
        "🔄 " + t("action.sync", "Sync Project"),
        "confirmSync",
        name,
      ),
    );
  }

  const header = createEl("div", { className: "issue-header" }, [
    createEl("div", {
      className: `issue-icon ${status}`,
      text: icon,
    }),
    createEl("div", { className: "issue-content", style: "flex: 1;" }, [
      createEl("div", { className: "issue-title" }, [
        createEl("span", { className: "issue-name", text: name }),
        createEl("span", {
          text: columns.typeLabel,
          style: "margin-left: 0.5rem; color: var(--color-fg-muted);",
        }),
      ]),
      createEl("div", {
        text: columns.message,
        style:
          "font-size: 0.875rem; color: var(--color-fg-muted); margin-top: 0.25rem;",
      }),
    ]),
  ]);

  const statusColumns = createEl("div", { className: "issue-status-columns" }, [
    statusColumn(t("column.local", "Local"), columns.local),
    statusColumn(t("column.project", "Project"), columns.project),
    statusColumn(
      t("column.repository", "Gitea Repository"),
      columns.repository,
    ),
  ]);

  return createEl(
    "div",
    { className: "issue-item issue-card", attrs: { "data-status": status } },
    [header, statusColumns, actions],
  );
}

/**
 * Renders the list of issues
 */
export function renderIssues(data: HealthData): void {
  const issues = data.issues;
  const issuesListEl = document.getElementById("issues-list");

  if (!issuesListEl) {
    return;
  }

  if (issues.length === 0) {
    issuesListEl.replaceChildren(
      createEl("div", { className: "empty-state" }, [
        createEl("div", { className: "empty-state-icon", text: "✓" }),
        createEl("div", {
          className: "empty-state-title",
          text: t("empty.title", "All projects are healthy!"),
        }),
        createEl("div", {
          className: "empty-state-message",
          text: t("empty.message", "No synchronization issues detected"),
        }),
      ]),
    );
    return;
  }

  issuesListEl.replaceChildren(...issues.map((issue) => renderIssue(issue)));
}

/**
 * Applies the current filter to visible cards
 */
export function applyFilter(filter: FilterType): void {
  const issueCards = document.querySelectorAll(".issue-card");
  let visibleCount = 0;

  issueCards.forEach((card) => {
    const htmlCard = card as HTMLElement;
    let shouldShow = false;

    if (filter === "all") {
      shouldShow = true;
    } else if (filter === "healthy") {
      shouldShow = card.getAttribute("data-status") === "healthy";
    } else if (filter === "warnings") {
      shouldShow = card.getAttribute("data-status") === "warning";
    } else if (filter === "critical") {
      shouldShow = card.getAttribute("data-status") === "critical";
    }

    if (shouldShow) {
      htmlCard.style.display = "";
      visibleCount++;
    } else {
      htmlCard.style.display = "none";
    }
  });

  console.log(
    `[Project Health] Showing ${visibleCount}/${issueCards.length} projects`,
  );
}
