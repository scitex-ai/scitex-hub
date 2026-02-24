/**
 * Markdown Renderer for AI Chat Messages
 * Uses marked.js (CDN-loaded) + DOMPurify for safe HTML rendering.
 */

declare const marked: { parse: (src: string) => string };
declare const DOMPurify: { sanitize: (html: string, cfg?: object) => string };

const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    "p",
    "br",
    "strong",
    "em",
    "code",
    "pre",
    "blockquote",
    "ul",
    "ol",
    "li",
    "a",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
    "hr",
    "span",
    "del",
    "sup",
    "sub",
  ],
  ALLOWED_ATTR: [
    "href",
    "target",
    "rel",
    "src",
    "alt",
    "title",
    "class",
    "colspan",
    "rowspan",
  ],
};

/** Check if marked.js and DOMPurify are available */
function isAvailable(): boolean {
  return (
    typeof marked !== "undefined" &&
    typeof marked.parse === "function" &&
    typeof DOMPurify !== "undefined" &&
    typeof DOMPurify.sanitize === "function"
  );
}

/** Render markdown text to sanitized HTML string */
export function renderMarkdown(text: string): string {
  if (!text.trim()) return "";
  if (!isAvailable()) return escapeHtml(text);

  try {
    const raw = marked.parse(text);
    const html = DOMPurify.sanitize(raw, PURIFY_CONFIG);
    return html;
  } catch {
    return escapeHtml(text);
  }
}

/** Highlight code blocks after inserting markdown HTML into DOM */
export function highlightCodeBlocks(container: HTMLElement): void {
  const hljs = (window as any).hljs;
  if (!hljs) return;
  container.querySelectorAll<HTMLElement>("pre code").forEach((block) => {
    hljs.highlightElement(block);
  });
}

/** Make external links open in new tab */
export function fixExternalLinks(container: HTMLElement): void {
  container.querySelectorAll<HTMLAnchorElement>("a[href]").forEach((a) => {
    if (a.hostname !== window.location.hostname) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
  });
}

function escapeHtml(text: string): string {
  const el = document.createElement("span");
  el.textContent = text;
  return el.innerHTML;
}
