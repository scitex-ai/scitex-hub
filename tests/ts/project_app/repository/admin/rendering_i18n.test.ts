/**
 * Project Health rendering reads the i18n catalog and never parses text as HTML.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  resetCatalog,
  CATALOG_ELEMENT_ID,
} from "@project_app/repository/admin/i18n";
import {
  renderIssues,
  renderIssue,
} from "@project_app/repository/admin/rendering";
import type { RepositoryIssue } from "@project_app/repository/admin/types";

function setUpPage(catalog: Record<string, string>): void {
  const script = document.createElement("script");
  script.id = CATALOG_ELEMENT_ID;
  script.type = "application/json";
  script.textContent = JSON.stringify(catalog);
  const list = document.createElement("div");
  list.id = "issues-list";
  document.body.replaceChildren(script, list);
  resetCatalog();
}

describe("project health rendering i18n", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    resetCatalog();
  });

  it("renders the empty-state title from the catalog", () => {
    // Arrange
    setUpPage({ "empty.title": "すべてのプロジェクトが正常です" });
    // Act
    renderIssues({
      success: true,
      stats: {
        healthy_count: 0,
        warnings: 0,
        critical_issues: 0,
        total_django_projects: 0,
      },
      issues: [],
    });
    // Assert
    expect(document.querySelector(".empty-state-title")?.textContent).toBe(
      "すべてのプロジェクトが正常です",
    );
  });

  it("renders the sync button label from the catalog", () => {
    // Arrange
    setUpPage({ "action.sync": "プロジェクトを同期" });
    const issue: RepositoryIssue = {
      is_healthy: false,
      is_critical: true,
      project_slug: "demo",
      issue_type: "missing_in_gitea",
      message: "Django project exists but Gitea repository not found",
    };
    // Act
    const card = renderIssue(issue);
    // Assert
    expect(card.querySelector(".issue-button")?.textContent).toBe(
      "🔄 プロジェクトを同期",
    );
  });

  it("renders a markup-like project name as text, not as elements", () => {
    // Arrange
    setUpPage({});
    const issue: RepositoryIssue = {
      is_healthy: true,
      is_critical: false,
      project_slug: '<img src="x" onerror="alert(1)">',
      issue_type: "healthy",
      message: "Repository healthy and in sync",
    };
    // Act
    const card = renderIssue(issue);
    // Assert
    expect(card.querySelector("img")).toBeNull();
  });
});
