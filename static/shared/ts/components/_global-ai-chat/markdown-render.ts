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
      marked.use({ gfm: true, breaks: false });
      _markedConfigured = true;
    }
    const protected_ = protectMath(text);
    const raw = marked.parse(protected_);
    const linked = linkifyUrls(raw);
    const html = DOMPurify.sanitize(linked, PURIFY_CONFIG);
    return html;
  } catch {
    return escapeHtml(text);
  }
}

/**
 * Pull LaTeX math out before marked.js mangles it (backslashes,
 * underscores, asterisks are all markdown-active). Display math
 * `$$...$$` / `\[...\]` first, then inline `\(...\)`. Each span becomes
 * `<span class="stx-math" data-tex="<base64>" data-display="1|0"></span>`,
 * rendered by renderMathBlocks() after DOM insert. Plain `$...$` is
 * deliberately NOT treated as math (currency false-positives).
 */
function protectMath(text: string): string {
  const enc = (tex: string, display: boolean): string =>
    `<span class="stx-math" data-tex="${b64encode(tex)}" data-display="${
      display ? "1" : "0"
    }"></span>`;
  // Fenced code blocks: leave math inside code alone (restore afterwards)
  const codeSpans: string[] = [];
  let out = text.replace(/```[\s\S]*?(?:```|$)/g, (m) => {
    codeSpans.push(m);
    return `\u0000CODE${codeSpans.length - 1}\u0000`;
  });
  out = out.replace(
    /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g,
    (_m, a, b) => enc(a ?? b, true),
  );
  out = out.replace(/\\\(([\s\S]+?)\\\)/g, (_m, a) => enc(a, false));
  return out.replace(/\u0000CODE(\d+)\u0000/g, (_m, i) => codeSpans[Number(i)]);
}

function b64encode(s: string): string {
  return btoa(
    encodeURIComponent(s).replace(/%([0-9A-F]{2})/g, (_m, h) =>
      String.fromCharCode(parseInt(h, 16)),
    ),
  );
}

function b64decode(s: string): string {
  return decodeURIComponent(
    Array.from(atob(s), (c) => `%${c.charCodeAt(0).toString(16).padStart(2, "0")}`).join(
      "",
    ),
  );
}

let _katexLoading: Promise<unknown> | null = null;

/** Render protected math spans inside a container with KaTeX (lazy-loaded) */
export async function renderMathBlocks(container: HTMLElement): Promise<void> {
  const spans = container.querySelectorAll<HTMLElement>("span.stx-math[data-tex]");
  if (!spans.length) return;
  try {
    if (!_katexLoading) {
      _katexLoading = Promise.all([
        import("katex"),
        import("katex/dist/katex.min.css"),
      ]);
    }
    const [{ default: katex }] = (await _katexLoading) as [
      { default: { render: (...args: unknown[]) => void } },
    ];
    spans.forEach((el) => {
      try {
        katex.render(b64decode(el.dataset.tex || ""), el, {
          displayMode: el.dataset.display === "1",
          throwOnError: false,
        } as unknown as undefined);
      } catch {
        /* keep raw TeX text on failure */
      }
    });
  } catch (err) {
    console.error("[MathRender]", err);
  }
}

/** Friendly display names for common fenced-code language tags */
const LANGUAGE_LABELS: Record<string, string> = {
  js: "JavaScript",
  ts: "TypeScript",
  py: "Python",
  sh: "Bash",
  yml: "YAML",
  md: "Markdown",
  tex: "LaTeX",
};

/** Highlight code blocks after inserting markdown HTML into DOM */
export function highlightCodeBlocks(container: HTMLElement): void {
  const hljs = (window as any).hljs;
  container.querySelectorAll<HTMLElement>("pre code").forEach((block) => {
    // Render mermaid code blocks as diagrams
    if (
      block.classList.contains("language-mermaid") ||
      block.classList.contains("mermaid")
    ) {
      renderMermaidBlock(block);
      return;
    }
    // Render graphviz/dot code blocks as diagrams
    if (
      block.classList.contains("language-dot") ||
      block.classList.contains("language-graphviz")
    ) {
      renderGraphvizBlock(block);
      return;
    }
    if (hljs) hljs.highlightElement(block);
    enhanceCodeBlock(block);
  });
}

/**
 * ChatGPT-style code-block chrome: a header row with the language label
 * (from the fenced `language-*` class) and a Copy button. Idempotent —
 * streaming re-renders call highlightCodeBlocks per segment, so skip
 * blocks already wrapped.
 */
function enhanceCodeBlock(block: HTMLElement): void {
  const pre = block.parentElement;
  if (!pre || pre.tagName !== "PRE") return;
  if (pre.parentElement?.classList.contains("stx-codeblock")) return;
  const langClass = Array.from(block.classList).find((c) =>
    c.startsWith("language-"),
  );
  const raw = langClass ? langClass.slice("language-".length) : "";
  const label = LANGUAGE_LABELS[raw] || raw || "code";

  const wrap = document.createElement("div");
  wrap.className = "stx-codeblock";
  const header = document.createElement("div");
  header.className = "stx-codeblock-header";
  const lang = document.createElement("span");
  lang.className = "stx-codeblock-lang";
  lang.textContent = label;
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "stx-codeblock-copy";
  copy.textContent = "Copy";
  copy.addEventListener("click", () => {
    const done = () => {
      copy.textContent = "Copied";
      setTimeout(() => (copy.textContent = "Copy"), 1500);
    };
    const text = block.textContent || "";
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
    } else {
      fallbackCopy(text, done);
    }
  });
  header.appendChild(lang);
  header.appendChild(copy);
  pre.replaceWith(wrap);
  wrap.appendChild(header);
  wrap.appendChild(pre);
}

function fallbackCopy(text: string, done: () => void): void {
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    done();
  } catch {
    /* clipboard unavailable — leave button as-is */
  }
}

/** Render a mermaid code block as an SVG diagram inline */
async function renderMermaidBlock(block: HTMLElement): Promise<void> {
  const code = block.textContent?.trim();
  if (!code) return;
  const pre = block.parentElement;
  if (!pre || pre.tagName !== "PRE") return;
  try {
    const { default: mermaid } = await import("mermaid");
    mermaid.initialize({
      startOnLoad: false,
      theme:
        document.documentElement.getAttribute("data-theme") === "dark"
          ? "dark"
          : "default",
      securityLevel: "loose",
    });
    const id = `mmd-chat-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const wrapper = document.createElement("div");
    wrapper.className = "stx-shell-ai-mermaid-diagram";
    wrapper.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
    pre.replaceWith(wrapper);
    await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
  } catch (err) {
    console.error("[MermaidRender]", err);
  }
}

/** Render a graphviz/dot code block as an SVG diagram inline */
async function renderGraphvizBlock(block: HTMLElement): Promise<void> {
  const code = block.textContent?.trim();
  if (!code) return;
  const pre = block.parentElement;
  if (!pre || pre.tagName !== "PRE") return;
  try {
    const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
    const graphviz = await Graphviz.load();
    const svg = graphviz.dot(code);
    const wrapper = document.createElement("div");
    wrapper.className = "stx-shell-ai-mermaid-diagram";
    wrapper.innerHTML = svg;
    pre.replaceWith(wrapper);
  } catch (err) {
    console.error("[GraphvizRender]", err);
  }
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
