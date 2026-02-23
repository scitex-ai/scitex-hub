/**
 * File Preview Panel — shows file content in the bottom of the worktree pane.
 * Triggered on file click (not hover). Supports text, images, and fallback.
 */

const IMAGE_EXTS = new Set([
  "png",
  "jpg",
  "jpeg",
  "gif",
  "svg",
  "webp",
  "bmp",
  "ico",
]);
const BINARY_EXTS = new Set([
  "pdf",
  "zip",
  "tar",
  "gz",
  "bz2",
  "7z",
  "rar",
  "exe",
  "dll",
  "so",
  "dylib",
  "whl",
  "egg",
  "mp3",
  "mp4",
  "wav",
  "avi",
  "mov",
  "npy",
  "npz",
  "pkl",
  "pickle",
  "h5",
  "hdf5",
]);
const MAX_PREVIEW_SIZE = 50_000; // 50KB text preview limit

function getExt(path: string): string {
  const dot = path.lastIndexOf(".");
  return dot >= 0 ? path.slice(dot + 1).toLowerCase() : "";
}

export class FilePreviewPanel {
  private el: HTMLElement;
  private contentEl: HTMLElement;
  private titleEl: HTMLElement;
  private openLink: HTMLAnchorElement | null;
  private username = "";
  private slug = "";

  constructor(container: HTMLElement) {
    this.el = container;
    this.titleEl = container.querySelector(".ws-preview-title") || container;
    this.contentEl =
      container.querySelector(".ws-preview-content") || container;
    this.openLink = container.querySelector(".ws-preview-open");
  }

  configure(username: string, slug: string): void {
    this.username = username;
    this.slug = slug;
  }

  async show(path: string): Promise<void> {
    if (!path || !this.username || !this.slug) return;

    const filename = path.split("/").pop() || path;
    const ext = getExt(filename);
    this.el.style.display = "";
    this.titleEl.textContent = filename;
    this.titleEl.title = path;
    if (this.openLink) {
      this.openLink.href = `/${this.username}/${this.slug}/blob/${path}`;
    }
    this.contentEl.innerHTML =
      '<div class="ws-preview-loading"><i class="fas fa-spinner fa-spin"></i></div>';

    if (IMAGE_EXTS.has(ext)) {
      this.showImage(path);
      return;
    }

    if (BINARY_EXTS.has(ext)) {
      this.showBinary(path, filename);
      return;
    }

    // Text file — fetch raw content
    await this.showText(path);
  }

  hide(): void {
    this.el.style.display = "none";
    this.contentEl.innerHTML = "";
    this.titleEl.textContent = "";
  }

  private showImage(path: string): void {
    const url = `/${this.username}/${this.slug}/blob/${path}?mode=raw`;
    this.contentEl.innerHTML = `<img class="ws-preview-image" src="${url}" alt="${path}" />`;
  }

  private showBinary(path: string, filename: string): void {
    const url = `/${this.username}/${this.slug}/blob/${path}?mode=raw`;
    this.contentEl.innerHTML = `
      <div class="ws-preview-binary">
        <i class="fas fa-file"></i>
        <span>${filename}</span>
        <a href="${url}" download class="ws-preview-download">
          <i class="fas fa-download"></i> Download
        </a>
      </div>`;
  }

  private async showText(path: string): Promise<void> {
    try {
      const url = `/${this.username}/${this.slug}/blob/${path}?mode=raw`;
      const resp = await fetch(url);
      if (!resp.ok) {
        this.contentEl.innerHTML = `<div class="ws-preview-error">Cannot load file (${resp.status})</div>`;
        return;
      }

      const contentType = resp.headers.get("content-type") || "";
      if (contentType.startsWith("image/")) {
        this.showImage(path);
        return;
      }

      const text = await resp.text();
      const truncated = text.length > MAX_PREVIEW_SIZE;
      const display = truncated ? text.slice(0, MAX_PREVIEW_SIZE) : text;

      const pre = document.createElement("pre");
      pre.className = "ws-preview-code";
      pre.textContent = display;
      this.contentEl.innerHTML = "";
      this.contentEl.appendChild(pre);

      if (truncated) {
        const note = document.createElement("div");
        note.className = "ws-preview-truncated";
        note.textContent = `Showing first ${(MAX_PREVIEW_SIZE / 1000).toFixed(0)}KB of ${(text.length / 1000).toFixed(0)}KB`;
        this.contentEl.appendChild(note);
      }
    } catch {
      this.contentEl.innerHTML =
        '<div class="ws-preview-error">Failed to load preview</div>';
    }
  }
}
