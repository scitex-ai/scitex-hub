/**
 * MarkdownPreview - Rich markdown renderer for the workspace viewer.
 *
 * Renders markdown with:
 * - Inline images (resolved via project file API)
 * - Expandable cards (<details> blocks)
 * - Audio/video players (links to media files)
 * - Tables (standard markdown tables)
 * - Syntax-highlighted code blocks
 */

/** Build a URL for a project file (image, audio, video). */
function resolveFileUrl(src: string, projectId: string): string {
  // Already absolute or external URL — leave as-is
  if (
    src.startsWith("http://") ||
    src.startsWith("https://") ||
    src.startsWith("data:")
  ) {
    return src;
  }
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  params.set("raw", "true");
  return `/api/workspace/file-content/${src}?${params.toString()}`;
}

/** Check if a URL points to an audio file. */
function isAudioUrl(url: string): boolean {
  return /\.(mp3|wav|ogg|flac|aac|m4a)(\?|$)/i.test(url);
}

/** Check if a URL points to a video file. */
function isVideoUrl(url: string): boolean {
  return /\.(mp4|webm|ogv|mov|avi)(\?|$)/i.test(url);
}

/** Escape HTML special characters. */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Render markdown to HTML with rich media support.
 * Uses a simple line-by-line parser (no external dependencies).
 */
export function renderMarkdown(markdown: string, projectId: string): string {
  const lines = markdown.split("\n");
  const html: string[] = [];
  let inCodeBlock = false;
  let codeLanguage = "";
  let codeLines: string[] = [];
  let inTable = false;
  let tableRows: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code blocks
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        html.push(renderCodeBlock(codeLines.join("\n"), codeLanguage));
        codeLines = [];
        codeLanguage = "";
        inCodeBlock = false;
      } else {
        flushTable();
        codeLanguage = line.slice(3).trim();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    // Table rows
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      tableRows.push(line);
      inTable = true;
      continue;
    } else if (inTable) {
      flushTable();
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = renderInline(headingMatch[2], projectId);
      html.push(`<h${level} class="md-heading">${text}</h${level}>`);
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|_{3,}|\*{3,})$/.test(line.trim())) {
      html.push("<hr>");
      continue;
    }

    // HTML pass-through (details, summary, etc.)
    if (line.trim().startsWith("<")) {
      html.push(line);
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      html.push("");
      continue;
    }

    // List items
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)$/);
    if (ulMatch) {
      html.push(
        `<li class="md-list-item">${renderInline(ulMatch[2], projectId)}</li>`,
      );
      continue;
    }

    const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
    if (olMatch) {
      html.push(
        `<li class="md-list-item">${renderInline(olMatch[2], projectId)}</li>`,
      );
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      html.push(
        `<blockquote class="md-blockquote">${renderInline(line.slice(2), projectId)}</blockquote>`,
      );
      continue;
    }

    // Regular paragraph
    html.push(`<p>${renderInline(line, projectId)}</p>`);
  }

  // Flush remaining
  if (inCodeBlock) {
    html.push(renderCodeBlock(codeLines.join("\n"), codeLanguage));
  }
  flushTable();

  return html.join("\n");

  function flushTable(): void {
    if (!inTable || tableRows.length === 0) return;
    html.push(renderTable(tableRows));
    tableRows = [];
    inTable = false;
  }
}

/** Render inline markdown (bold, italic, code, links, images). */
function renderInline(text: string, projectId: string): string {
  // Images: ![alt](src) — may render as audio/video player
  text = text.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    (_match, alt: string, src: string) => {
      const resolvedSrc = resolveFileUrl(src, projectId);
      if (isAudioUrl(src)) {
        return `<div class="md-player"><audio controls preload="metadata"><source src="${escapeHtml(resolvedSrc)}"></audio><span class="md-player-label">${escapeHtml(alt || src)}</span></div>`;
      }
      if (isVideoUrl(src)) {
        return `<div class="md-player"><video controls preload="metadata" style="max-width:100%"><source src="${escapeHtml(resolvedSrc)}"></video></div>`;
      }
      return `<img class="md-image" src="${escapeHtml(resolvedSrc)}" alt="${escapeHtml(alt)}" loading="lazy">`;
    },
  );

  // Links: [text](url)
  text = text.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_match, label: string, href: string) => {
      // Media links rendered as players
      if (isAudioUrl(href)) {
        const resolvedHref = resolveFileUrl(href, projectId);
        return `<div class="md-player"><audio controls preload="metadata"><source src="${escapeHtml(resolvedHref)}"></audio><span class="md-player-label">${escapeHtml(label)}</span></div>`;
      }
      if (isVideoUrl(href)) {
        const resolvedHref = resolveFileUrl(href, projectId);
        return `<div class="md-player"><video controls preload="metadata" style="max-width:100%"><source src="${escapeHtml(resolvedHref)}"></video></div>`;
      }
      return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
    },
  );

  // Bold: **text** or __text__
  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/__(.+?)__/g, "<strong>$1</strong>");

  // Italic: *text* or _text_
  text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
  text = text.replace(/_(.+?)_/g, "<em>$1</em>");

  // Inline code: `code`
  text = text.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

  // Strikethrough: ~~text~~
  text = text.replace(/~~(.+?)~~/g, "<del>$1</del>");

  return text;
}

/** Render a fenced code block. */
function renderCodeBlock(code: string, language: string): string {
  const langClass = language ? ` data-language="${escapeHtml(language)}"` : "";
  const langLabel = language
    ? `<span class="md-code-lang">${escapeHtml(language)}</span>`
    : "";
  return `<div class="md-code-block"${langClass}>${langLabel}<pre><code>${escapeHtml(code)}</code></pre></div>`;
}

/** Render a markdown table from pipe-delimited rows. */
function renderTable(rows: string[]): string {
  if (rows.length === 0) return "";

  const parseRow = (row: string): string[] =>
    row
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());

  // Check if row 2 is a separator (---|----|---)
  const isSeparator = (row: string): boolean =>
    /^\|[\s:]*-{2,}[\s:]*(\|[\s:]*-{2,}[\s:]*)*\|$/.test(row.trim());

  const html: string[] = ['<table class="md-table">'];

  let headerDone = false;
  for (let i = 0; i < rows.length; i++) {
    if (isSeparator(rows[i])) {
      headerDone = true;
      continue;
    }
    const cells = parseRow(rows[i]);
    const tag = !headerDone ? "th" : "td";
    const rowTag = !headerDone ? "thead" : "";
    if (!headerDone) html.push("<thead>");
    html.push("<tr>");
    for (const cell of cells) {
      html.push(`<${tag}>${cell}</${tag}>`);
    }
    html.push("</tr>");
    if (!headerDone) {
      html.push("</thead><tbody>");
      headerDone = true;
    }
  }

  html.push("</tbody></table>");
  return html.join("");
}

/**
 * MarkdownPreviewPanel - manages a preview container that renders markdown.
 */
export class MarkdownPreviewPanel {
  private container: HTMLElement;
  private projectId: string = "";

  constructor(container: HTMLElement) {
    this.container = container;
  }

  setProjectId(id: string): void {
    this.projectId = id;
  }

  /** Render markdown content into the preview container. */
  render(content: string): void {
    this.container.innerHTML = "";
    const wrapper = document.createElement("div");
    wrapper.className = "md-preview-content";
    wrapper.innerHTML = renderMarkdown(content, this.projectId);
    this.container.appendChild(wrapper);
  }
}
