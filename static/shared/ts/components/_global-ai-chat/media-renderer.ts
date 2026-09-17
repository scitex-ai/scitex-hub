/**
 * Media Renderer for AI Chat
 * Renders inline images, CSV tables, PDF links, and file links from MCP tool results.
 */

export interface MediaRef {
  type:
    | "image"
    | "pdf"
    | "csv"
    | "plotly"
    | "mermaid"
    | "graphviz"
    | "audio"
    | "video";
  path: string;
  ext: string;
}

/** Encode one untrusted route segment using the stricter RFC 3986 set. */
function encodeSegment(segment: string): string {
  return encodeURIComponent(segment).replace(
    /[!'()*]/g,
    (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

/** Encode an untrusted file path while preserving its path separators. */
function encodePath(path: string): string {
  return path.split("/").map(encodeSegment).join("/");
}

/** Build raw blob URL for serving file content */
function blobUrl(username: string, slug: string, path: string): string {
  return `/${encodeSegment(username)}/${encodeSegment(slug)}/blob/${encodePath(path)}?mode=raw`;
}

/** Build navigable blob URL (file view page) */
function viewUrl(username: string, slug: string, path: string): string {
  return `/${encodeSegment(username)}/${encodeSegment(slug)}/blob/${encodePath(path)}`;
}

/** Extract filename from path */
function filename(path: string): string {
  return path.split("/").pop() || path;
}

/** Read diagram text from the JSON response shape without trusting its type. */
function jsonContent(value: unknown): string {
  if (typeof value !== "object" || value === null || !("content" in value)) {
    return "";
  }
  const content = (value as { content: unknown }).content;
  return typeof content === "string" ? content : "";
}

/** Build the allowlisted file-link structure without parsing HTML text. */
function createFileLink(
  ref: MediaRef,
  username: string,
  slug: string,
  iconClass: string,
): HTMLAnchorElement {
  const link = document.createElement("a");
  link.className = "stx-shell-ai-media-file";
  link.href = viewUrl(username, slug, ref.path);
  link.target = "_blank";
  link.rel = "noopener noreferrer";

  const icon = document.createElement("i");
  icon.classList.add("fas", iconClass);
  icon.setAttribute("aria-hidden", "true");
  link.append(icon, document.createTextNode(filename(ref.path)));
  return link;
}

/** Append a filename caption using text-only DOM APIs. */
function appendCaption(wrapper: HTMLElement, path: string): void {
  const caption = document.createElement("span");
  caption.className = "stx-shell-ai-media-caption";
  caption.textContent = filename(path);
  wrapper.appendChild(caption);
}

/**
 * Render generated SVG in the browser's inert image context.
 *
 * Mermaid and Graphviz output can be derived from attacker-controlled repository
 * text. SVG loaded as an image cannot execute scripts or event handlers, unlike
 * the same text inserted into the active document through an HTML parsing sink.
 */
function appendSvgImage(wrapper: HTMLElement, svg: string, path: string): void {
  const objectUrl = URL.createObjectURL(
    new Blob([svg], { type: "image/svg+xml;charset=utf-8" }),
  );
  const image = document.createElement("img");
  image.src = objectUrl;
  image.alt = filename(path);
  image.className = "stx-shell-ai-media-diagram-image";

  const revokeObjectUrl = () => URL.revokeObjectURL(objectUrl);
  image.addEventListener("load", revokeObjectUrl, { once: true });
  image.addEventListener("error", revokeObjectUrl, { once: true });

  wrapper.replaceChildren(image);
  appendCaption(wrapper, path);
}

/** Render a media reference into a DOM element */
export function renderMedia(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  switch (ref.type) {
    case "image":
      return renderImage(ref, username, slug);
    case "csv":
      return renderCsv(ref, username, slug);
    case "audio":
      return renderAudio(ref, username, slug);
    case "video":
      return renderVideo(ref, username, slug);
    case "pdf":
      return renderFileLink(ref, username, slug, "fa-file-pdf");
    case "plotly":
      return renderFileLink(ref, username, slug, "fa-chart-line");
    case "mermaid":
      return renderMermaid(ref, username, slug);
    case "graphviz":
      return renderGraphviz(ref, username, slug);
    default:
      return renderFileLink(ref, username, slug, "fa-file");
  }
}

function renderImage(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media stx-shell-ai-media-image";

  const img = document.createElement("img");
  img.src = blobUrl(username, slug, ref.path);
  img.alt = filename(ref.path);
  img.loading = "lazy";
  img.addEventListener("click", () =>
    window.open(
      viewUrl(username, slug, ref.path),
      "_blank",
      "noopener,noreferrer",
    ),
  );
  wrapper.appendChild(img);
  appendCaption(wrapper, ref.path);

  return wrapper;
}

function renderCsv(ref: MediaRef, username: string, slug: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media stx-shell-ai-media-table";
  wrapper.textContent = "Loading...";

  // Fetch CSV and render table (first 10 rows)
  fetch(blobUrl(username, slug, ref.path))
    .then((r) => r.text())
    .then((text) => {
      const lines = text.trim().split("\n").slice(0, 11); // header + 10 rows
      if (lines.length === 0) {
        wrapper.textContent = "(empty)";
        return;
      }
      const table = document.createElement("table");
      lines.forEach((line, i) => {
        const row = document.createElement("tr");
        const cells = line.split(",");
        cells.forEach((cell) => {
          const el = document.createElement(i === 0 ? "th" : "td");
          el.textContent = cell.trim();
          row.appendChild(el);
        });
        table.appendChild(row);
      });
      wrapper.textContent = "";
      wrapper.appendChild(table);
      appendCaption(wrapper, ref.path);
    })
    .catch(() => {
      wrapper.textContent = `Could not load: ${filename(ref.path)}`;
    });

  return wrapper;
}

function renderAudio(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media stx-shell-ai-media-audio";

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.src = blobUrl(username, slug, ref.path);
  wrapper.appendChild(audio);
  appendCaption(wrapper, ref.path);

  return wrapper;
}

function renderVideo(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media stx-shell-ai-media-video";

  const video = document.createElement("video");
  video.controls = true;
  video.preload = "metadata";
  video.style.maxWidth = "100%";
  video.style.borderRadius = "4px";
  video.src = blobUrl(username, slug, ref.path);
  wrapper.appendChild(video);
  appendCaption(wrapper, ref.path);

  return wrapper;
}

function renderMermaid(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media stx-shell-ai-mermaid-diagram";
  wrapper.textContent = "Loading diagram...";

  fetch(blobUrl(username, slug, ref.path))
    .then((r) => {
      const ct = r.headers.get("content-type") || "";
      return ct.includes("application/json")
        ? r.json().then(jsonContent)
        : r.text();
    })
    .then(async (code: string) => {
      code = code.trim();
      if (!code) {
        wrapper.textContent = "(empty diagram)";
        return;
      }
      const { default: mermaid } = await import("mermaid");
      mermaid.initialize({
        startOnLoad: false,
        theme:
          document.documentElement.getAttribute("data-theme") === "dark"
            ? "dark"
            : "default",
        securityLevel: "strict",
      });
      const id = `mmd-media-${Date.now()}`;
      const { svg } = await mermaid.render(id, code);
      appendSvgImage(wrapper, svg, ref.path);
    })
    .catch(() => {
      wrapper.replaceChildren(
        createFileLink(ref, username, slug, "fa-project-diagram"),
      );
    });

  return wrapper;
}

function renderGraphviz(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media stx-shell-ai-mermaid-diagram";
  wrapper.textContent = "Loading diagram...";

  fetch(blobUrl(username, slug, ref.path))
    .then((r) => {
      const ct = r.headers.get("content-type") || "";
      return ct.includes("application/json")
        ? r.json().then(jsonContent)
        : r.text();
    })
    .then(async (code: string) => {
      code = code.trim();
      if (!code) {
        wrapper.textContent = "(empty diagram)";
        return;
      }
      const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
      const graphviz = await Graphviz.load();
      const svg = graphviz.dot(code);
      appendSvgImage(wrapper, svg, ref.path);
    })
    .catch(() => {
      wrapper.replaceChildren(
        createFileLink(ref, username, slug, "fa-project-diagram"),
      );
    });

  return wrapper;
}

function renderFileLink(
  ref: MediaRef,
  username: string,
  slug: string,
  iconClass: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-media";
  wrapper.appendChild(createFileLink(ref, username, slug, iconClass));
  return wrapper;
}
