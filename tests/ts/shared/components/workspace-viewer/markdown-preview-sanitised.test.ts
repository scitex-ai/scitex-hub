/**
 * Markdown renders as markdown, and the render is sanitised.
 *
 * Site audit 2026-09-14 (D12): AGENTS.md showed as raw markdown. The viewer
 * now opens .md rendered (with a Raw toggle). Files come from other people's
 * public projects too, so the renderer must never pass their HTML through.
 */

import { describe, it, expect } from "vitest";

import { renderMarkdown } from "@/components/workspace-viewer/_MarkdownPreview";

describe("markdown preview", () => {
  it("renders a heading as a heading", () => {
    // Arrange
    const source = "# dotfiles";
    // Act
    const html = renderMarkdown(source, "1");
    // Assert
    expect(html).toContain('<h1 class="md-heading">dotfiles</h1>');
  });

  it("does not pass raw HTML through", () => {
    // Arrange
    const source = '<img src="x" onerror="alert(1)">';
    // Act
    const html = renderMarkdown(source, "1");
    // Assert
    expect(html).not.toContain("<img");
  });

  it("does not emit a javascript: link", () => {
    // Arrange
    const source = "[click](javascript:alert(1))";
    // Act
    const html = renderMarkdown(source, "1");
    // Assert
    expect(html).not.toContain('href="javascript:');
  });

  it("escapes HTML inside inline text", () => {
    // Arrange
    const source = "see **<script>alert(1)</script>**";
    // Act
    const html = renderMarkdown(source, "1");
    // Assert
    expect(html).not.toContain("<script>");
  });
});
