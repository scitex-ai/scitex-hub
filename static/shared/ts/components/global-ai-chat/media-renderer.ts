/**
 * Media Renderer for AI Chat
 * Renders inline images, CSV tables, PDF links, and file links from MCP tool results.
 */

export interface MediaRef {
  type: "image" | "pdf" | "csv" | "plotly" | "mermaid";
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
    case "pdf":
      return renderFileLink(ref, username, slug, "fa-file-pdf");
    case "plotly":
      return renderFileLink(ref, username, slug, "fa-chart-line");
    case "mermaid":
      return renderFileLink(ref, username, slug, "fa-project-diagram");
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
