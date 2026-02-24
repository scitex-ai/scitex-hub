/**
 * Markdown Renderer for AI Chat Messages
 * Uses marked.js (CDN-loaded) + DOMPurify for safe HTML rendering.
 */

declare const marked: {
  parse: (src: string) => string;
  use: (opts: Record<string, unknown>) => void;
};
declare const DOMPurify: { sanitize: (html: string, cfg?: object) => string };

let _markedConfigured = false;

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

/**
 * Linkify bare URLs in HTML that are not already inside <a> or <code> tags.
 * Handles http://, https://, and www. prefixed URLs.
 */
function linkifyUrls(html: string): string {
  // Match bare URLs not already inside href="..." or <a>...</a> or <code>
  // Strategy: split on existing tags, only linkify text nodes
  const URL_RE = /(?<![=">])\b(https?:\/\/[^\s<>"')\]]+|www\.[^\s<>"')\]]+)/gi;

  return html.replace(
    /(<[^>]+>)|([^<]+)/g,
    (_match: string, tag: string, text: string) => {
      if (tag) return tag; // preserve HTML tags as-is
      // Linkify bare URLs in text content
      return text.replace(URL_RE, (url: string) => {
        const href = url.startsWith("www.") ? `https://${url}` : url;
        return `<a href="${href}">${url}</a>`;
      });
    },
  );
}

/** Render markdown text to sanitized HTML string */
export function renderMarkdown(text: string): string {
  if (!text.trim()) return "";
  if (!isAvailable()) return escapeHtml(text);

  try {
    if (!_markedConfigured) {
      marked.use({ gfm: true, breaks: true });
      _markedConfigured = true;
    }
    const raw = marked.parse(text);
    const linked = linkifyUrls(raw);
    const html = DOMPurify.sanitize(linked, PURIFY_CONFIG);
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
