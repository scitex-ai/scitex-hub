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

/** Build raw blob URL for serving file content */
function blobUrl(username: string, slug: string, path: string): string {
  return `/${username}/${slug}/blob/${path}?mode=raw`;
}

/** Build navigable blob URL (file view page) */
function viewUrl(username: string, slug: string, path: string): string {
  return `/${username}/${slug}/blob/${path}`;
}

/** Extract filename from path */
function filename(path: string): string {
  return path.split("/").pop() || path;
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
  wrapper.className = "scitex-ai-media scitex-ai-media-image";

  const img = document.createElement("img");
  img.src = blobUrl(username, slug, ref.path);
  img.alt = filename(ref.path);
  img.loading = "lazy";
  img.addEventListener("click", () =>
    window.open(viewUrl(username, slug, ref.path), "_blank"),
  );
  wrapper.appendChild(img);

  const caption = document.createElement("span");
  caption.className = "scitex-ai-media-caption";
  caption.textContent = filename(ref.path);
  wrapper.appendChild(caption);

  return wrapper;
}

function renderCsv(ref: MediaRef, username: string, slug: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "scitex-ai-media scitex-ai-media-table";
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

      // Add caption with filename
      const caption = document.createElement("span");
      caption.className = "scitex-ai-media-caption";
      caption.textContent = filename(ref.path);
      wrapper.appendChild(caption);
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
  wrapper.className = "scitex-ai-media scitex-ai-media-audio";

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.src = blobUrl(username, slug, ref.path);
  wrapper.appendChild(audio);

  const caption = document.createElement("span");
  caption.className = "scitex-ai-media-caption";
  caption.textContent = filename(ref.path);
  wrapper.appendChild(caption);

  return wrapper;
}

function renderVideo(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "scitex-ai-media scitex-ai-media-video";

  const video = document.createElement("video");
  video.controls = true;
  video.preload = "metadata";
  video.style.maxWidth = "100%";
  video.style.borderRadius = "4px";
  video.src = blobUrl(username, slug, ref.path);
  wrapper.appendChild(video);

  const caption = document.createElement("span");
  caption.className = "scitex-ai-media-caption";
  caption.textContent = filename(ref.path);
  wrapper.appendChild(caption);

  return wrapper;
}

function renderMermaid(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "scitex-ai-media scitex-ai-mermaid-diagram";
  wrapper.textContent = "Loading diagram...";

  fetch(blobUrl(username, slug, ref.path))
    .then((r) => {
      const ct = r.headers.get("content-type") || "";
      return ct.includes("application/json")
        ? r.json().then((j: any) => j.content ?? "")
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
        securityLevel: "loose",
      });
      const id = `mmd-media-${Date.now()}`;
      wrapper.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
      await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
      const caption = document.createElement("span");
      caption.className = "scitex-ai-media-caption";
      caption.textContent = filename(ref.path);
      wrapper.appendChild(caption);
    })
    .catch(() => {
      wrapper.innerHTML = `<a class="scitex-ai-media-file" href="${viewUrl(username, slug, ref.path)}" target="_blank"><i class="fas fa-project-diagram"></i>${filename(ref.path)}</a>`;
    });

  return wrapper;
}

function renderGraphviz(
  ref: MediaRef,
  username: string,
  slug: string,
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "scitex-ai-media scitex-ai-mermaid-diagram";
  wrapper.textContent = "Loading diagram...";

  fetch(blobUrl(username, slug, ref.path))
    .then((r) => {
      const ct = r.headers.get("content-type") || "";
      return ct.includes("application/json")
        ? r.json().then((j: any) => j.content ?? "")
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
      wrapper.innerHTML = svg;
      const caption = document.createElement("span");
      caption.className = "scitex-ai-media-caption";
      caption.textContent = filename(ref.path);
      wrapper.appendChild(caption);
    })
    .catch(() => {
      wrapper.innerHTML = `<a class="scitex-ai-media-file" href="${viewUrl(username, slug, ref.path)}" target="_blank"><i class="fas fa-project-diagram"></i>${filename(ref.path)}</a>`;
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
  wrapper.className = "scitex-ai-media";

  const link = document.createElement("a");
  link.className = "scitex-ai-media-file";
  link.href = viewUrl(username, slug, ref.path);
  link.target = "_blank";
  link.innerHTML = `<i class="fas ${iconClass}"></i>`;
  link.appendChild(document.createTextNode(filename(ref.path)));
  wrapper.appendChild(link);

  return wrapper;
}
