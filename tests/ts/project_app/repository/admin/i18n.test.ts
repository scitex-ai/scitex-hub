/**
 * Tests for apps/infra/project_app/static/project_app/ts/repository/admin/i18n.ts
 *
 * The Project Health template emits {{ catalog|json_script:"project-health-i18n" }};
 * t(key, fallbackEnglish) must read it, and fall back to the English source.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  t,
  resetCatalog,
  CATALOG_ELEMENT_ID,
} from "@project_app/repository/admin/i18n";

function installCatalog(catalog: Record<string, string>): void {
  const script = document.createElement("script");
  script.id = CATALOG_ELEMENT_ID;
  script.type = "application/json";
  script.textContent = JSON.stringify(catalog);
  document.body.replaceChildren(script);
  resetCatalog();
}

describe("project health i18n t()", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    resetCatalog();
  });

  it("returns the catalog value for a known key", () => {
    // Arrange
    installCatalog({ "error.sync": "プロジェクトを同期できませんでした" });
    // Act
    const text = t("error.sync", "Failed to sync project");
    // Assert
    expect(text).toBe("プロジェクトを同期できませんでした");
  });

  it("falls back to English when the key is missing from the catalog", () => {
    // Arrange
    installCatalog({ "error.sync": "プロジェクトを同期できませんでした" });
    // Act
    const text = t("error.connect", "Failed to connect to server");
    // Assert
    expect(text).toBe("Failed to connect to server");
  });

  it("falls back to English when the page ships no catalog", () => {
    // Arrange
    document.body.replaceChildren();
    // Act
    const text = t("error.sync", "Failed to sync project");
    // Assert
    expect(text).toBe("Failed to sync project");
  });
});
