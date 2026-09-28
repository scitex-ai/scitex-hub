import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const source = (path: string) =>
  readFileSync(resolve(process.cwd(), path), "utf8");

describe("CodeQL JavaScript and template regressions", () => {
  it("builds writer section dropdowns as DOM instead of HTML strings", () => {
    const controller = source(
      "apps/workspace/writer_app/static/writer_app/ts/utils/_section-dropdown/SectionDropdown.ts",
    );
    const renderer = source(
      "apps/workspace/writer_app/static/writer_app/ts/utils/_section-dropdown/rendering.ts",
    );
    expect(controller).not.toMatch(/dropdownContainer\.innerHTML\s*=/);
    expect(renderer).not.toMatch(/\.innerHTML\s*=/);
    expect(renderer).toContain("textContent");
  });

  it("uses DOM builders and safe project URLs for AI rich media", () => {
    const media = source(
      "static/shared/ts/components/_global-ai-chat/media-renderer.ts",
    );
    expect(media).not.toMatch(/\.innerHTML\s*=/);
    expect(media).toContain("encodeURIComponent");
    expect(media).toContain('new Blob([svg], { type: "image/svg+xml" })');
  });

  it("validates sidebar fallback navigation before assigning it", () => {
    const sidebar = source("static/shared/ts/components/sidebar/index.ts");
    expect(sidebar).toContain("safeSameOriginNavigationUrl");
    expect(sidebar).not.toMatch(/location\.href\s*=\s*href/);
  });

  it("constructs workspace viewer errors as text without logging paths", () => {
    const viewer = source(
      "static/shared/ts/components/workspace-viewer/index.ts",
    );
    expect(viewer).toContain('"[WorkspaceViewer] Failed to load a file"');
    expect(viewer).not.toMatch(/mediaContainer\.innerHTML\s*=/);
    expect(viewer).toContain("createViewerPlaceholder");
  });

  it("pins every remaining external template script with SHA-384 SRI", () => {
    for (const path of [
      "apps/workspace/writer_app/templates/writer_app/pdf_debug.html",
      "templates/global_base_partials/global_body_scripts.html",
    ]) {
      const html = source(path);
      const externalScripts = [
        ...html.matchAll(/<script\s+[^>]*src=["']https:\/\/[^"']+["'][^>]*>/g),
      ].map((m) => m[0]);
      expect(externalScripts.length).toBeGreaterThan(0);
      for (const tag of externalScripts) {
        expect(tag).toMatch(/integrity="sha384-[A-Za-z0-9+/=]+"/);
        expect(tag).toContain('crossorigin="anonymous"');
      }
    }
    const templates =
      source("apps/workspace/writer_app/templates/writer_app/pdf_debug.html") +
      source("templates/global_base_partials/global_body_scripts.html");
    for (const integrity of [
      "sha384-/1qUCSGwTur9vjf/z9lmu/eCUYbpOTgSjmpbMQZ1/CtX2v/WcAIKqRv+U1DUCG6e",
      "sha384-F/bZzf7p3Joyp5psL90p/p89AZJsndkSoGwRpXcZhleCWhd8SnRuoYo4d0yirjJp",
      "sha384-+ch8x/dgaV//v6Sa8m4v5+7KScnpCuxHqilN8njQ013CEKg3Fbd8Q3oN9tfpouLh",
      "sha384-zbcZAIxlvJtNE3Dp5nxLXdXtXyxwOdnILY1TDPVmKFhl4r4nSUG1r8bcFXGVa4Te",
      "sha384-cwS6YdhLI7XS60eoDiC+egV0qHp8zI+Cms46R0nbn8JrmoAzV9uFL60etMZhAnSu",
    ]) {
      expect(templates).toContain(`integrity="${integrity}"`);
    }
  });
});
