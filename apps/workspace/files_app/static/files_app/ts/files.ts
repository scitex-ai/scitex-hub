/**
 * Files app: browse and manage the signed-in user's whole workspace.
 */

import { getCsrfToken } from "@utils/csrf";

interface Entry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: number;
  project_url: string;
}

type Strings = Record<string, string>;

const API = "/apps/files/";
const PREVIEW_TEXT_LIMIT = 512 * 1024;
const IMAGE = /\.(png|jpe?g|gif|webp|bmp|avif)$/i;
const VIDEO = /\.(mp4|webm|mov|m4v|ogv)$/i;
const AUDIO = /\.(mp3|wav|ogg|m4a|flac)$/i;
const PDF = /\.pdf$/i;
const TEXT =
  /\.(txt|md|csv|tsv|json|ya?ml|py|r|m|tex|bib|log|sh|toml|ini|cfg|xml|html|css|js|ts|svg)$/i;

function byId<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

function fmt(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/%\((\w+)\)s/g, (_m, key) =>
    String(values[key] ?? ""),
  );
}

function humanSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${units[unit]}`;
}

function iconFor(entry: Entry): string {
  if (entry.is_dir) {
    if (entry.path === "Downloads") return "fa-download";
    if (entry.path === "Recordings") return "fa-video";
    return "fa-folder";
  }
  if (IMAGE.test(entry.name)) return "fa-file-image";
  if (VIDEO.test(entry.name)) return "fa-file-video";
  if (AUDIO.test(entry.name)) return "fa-file-audio";
  if (PDF.test(entry.name)) return "fa-file-pdf";
  if (TEXT.test(entry.name)) return "fa-file-lines";
  return "fa-file";
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
  text = "",
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function query(path: string): string {
  return `?path=${encodeURIComponent(path)}`;
}

class FilesApp {
  private strings: Strings;
  private current = "";
  private entries: Entry[] = [];
  private list = byId<HTMLUListElement>("files-list");
  private status = byId<HTMLParagraphElement>("files-status");
  private breadcrumb = byId<HTMLElement>("files-breadcrumb");
  private preview = byId<HTMLElement>("files-preview");
  private previewName = byId<HTMLElement>("files-preview-name");
  private previewContent = byId<HTMLElement>("files-preview-content");
  private backdrop = byId<HTMLElement>("files-sheet-backdrop");
  private sheetTitle = byId<HTMLElement>("files-sheet-title");
  private sheetBody = byId<HTMLElement>("files-sheet-body");

  constructor() {
    const raw = document.getElementById("files-strings")?.textContent || "{}";
    this.strings = JSON.parse(raw) as Strings;
  }

  private t(key: string): string {
    return this.strings[key] || key;
  }

  start(): void {
    this.bindToolbar();
    this.bindDragAndDrop();
    window.addEventListener("popstate", () => {
      void this.load(this.pathFromUrl(), false);
    });
    void this.load(this.pathFromUrl(), false);
  }

  private pathFromUrl(): string {
    return new URLSearchParams(window.location.search).get("path") || "";
  }

  private setStatus(message: string, isError = false): void {
    this.status.textContent = message;
    this.status.classList.toggle("files-status-error", isError);
  }

  private async request(url: string, init?: RequestInit): Promise<any> {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...init,
      headers: { "X-CSRFToken": getCsrfToken(), ...(init?.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || response.statusText);
    return data;
  }

  private post(endpoint: string, body: Record<string, string>): Promise<any> {
    return this.request(`${API}api/${endpoint}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private fail(error: unknown): void {
    const message = error instanceof Error ? error.message : String(error);
    this.setStatus(fmt(this.t("failed"), { error: message }), true);
  }

  async load(path: string, push = true): Promise<void> {
    try {
      const data = await this.request(`${API}api/list/${query(path)}`);
      this.current = data.path;
      this.entries = data.entries;
      if (push) {
        history.pushState(
          {},
          "",
          `${API}${this.current ? query(this.current) : ""}`,
        );
      }
      this.renderBreadcrumb();
      this.renderList();
      this.highlightPlace();
    } catch (error) {
      this.fail(error);
    }
  }

  private label(segment: string, depth: number): string {
    return depth === 0 && this.strings[segment]
      ? this.strings[segment]
      : segment;
  }

  private renderBreadcrumb(): void {
    this.breadcrumb.replaceChildren();
    const home = el("button", "files-crumb", this.t("home"));
    home.type = "button";
    home.addEventListener("click", () => void this.load(""));
    this.breadcrumb.append(home);
    const parts = this.current ? this.current.split("/") : [];
    parts.forEach((part, index) => {
      this.breadcrumb.append(el("span", "files-crumb-sep", "/"));
      const target = parts.slice(0, index + 1).join("/");
      const crumb = el("button", "files-crumb", this.label(part, index));
      crumb.type = "button";
      if (index === parts.length - 1)
        crumb.setAttribute("aria-current", "page");
      crumb.addEventListener("click", () => void this.load(target));
      this.breadcrumb.append(crumb);
    });
  }

  private highlightPlace(): void {
    document.querySelectorAll<HTMLElement>(".files-place").forEach((place) => {
      const path = place.dataset.path || "";
      const active =
        path === this.current ||
        (path !== "" && this.current.startsWith(`${path}/`));
      place.classList.toggle("is-active", active);
    });
  }

  private renderList(): void {
    this.list.replaceChildren();
    if (this.entries.length === 0) {
      this.list.append(el("li", "files-empty", this.t("empty")));
      return;
    }
    for (const entry of this.entries) {
      this.list.append(this.renderRow(entry));
    }
  }

  private renderRow(entry: Entry): HTMLLIElement {
    const row = el("li", "files-row");
    const main = el("button", "files-row-main");
    main.type = "button";
    const icon = el("i", `fas ${iconFor(entry)} files-row-icon`);
    icon.setAttribute("aria-hidden", "true");
    const text = el("span", "files-row-text");
    const depth = this.current ? 1 : 0;
    text.append(el("span", "files-row-name", this.label(entry.name, depth)));
    const when = new Date(entry.modified * 1000).toLocaleString();
    const meta = entry.is_dir ? when : `${humanSize(entry.size)} · ${when}`;
    text.append(el("span", "files-row-meta", meta));
    main.append(icon, text);
    main.addEventListener("click", () => this.open(entry));

    const more = el("button", "files-row-more");
    more.type = "button";
    more.setAttribute("aria-label", `${this.t("actions")}: ${entry.name}`);
    const dots = el("i", "fas fa-ellipsis-vertical");
    dots.setAttribute("aria-hidden", "true");
    more.append(dots);
    more.addEventListener("click", () => this.showActions(entry));

    row.append(main, more);
    return row;
  }

  private open(entry: Entry): void {
    if (entry.is_dir) {
      void this.load(entry.path);
    } else {
      this.showPreview(entry);
    }
  }

  private showPreview(entry: Entry): void {
    const src = `${API}raw/${query(entry.path)}`;
    this.previewName.textContent = entry.name;
    this.previewContent.replaceChildren();
    if (IMAGE.test(entry.name)) {
      const img = el("img", "files-preview-media");
      img.src = src;
      img.alt = entry.name;
      this.previewContent.append(img);
    } else if (VIDEO.test(entry.name)) {
      const video = el("video", "files-preview-media");
      video.src = src;
      video.controls = true;
      this.previewContent.append(video);
    } else if (AUDIO.test(entry.name)) {
      const audio = el("audio", "files-preview-audio");
      audio.src = src;
      audio.controls = true;
      this.previewContent.append(audio);
    } else if (PDF.test(entry.name)) {
      const frame = el("iframe", "files-preview-frame");
      frame.src = src;
      frame.title = entry.name;
      this.previewContent.append(frame);
    } else if (TEXT.test(entry.name) && entry.size <= PREVIEW_TEXT_LIMIT) {
      const pre = el("pre", "files-preview-text");
      this.previewContent.append(pre);
      fetch(src, { credentials: "same-origin" })
        .then((r) => r.text())
        .then((body) => {
          pre.textContent = body;
        })
        .catch((error) => this.fail(error));
    } else {
      this.previewContent.append(
        el("p", "files-preview-none", this.t("noPreview")),
      );
    }
    const actions = el("div", "files-preview-actions");
    actions.append(
      this.linkButton(
        this.t("download"),
        "fa-download",
        `${API}download/${query(entry.path)}`,
      ),
    );
    if (entry.project_url) {
      actions.append(
        this.linkButton(
          this.t("openInProject"),
          "fa-up-right-from-square",
          entry.project_url,
        ),
      );
    }
    this.previewContent.append(actions);
    this.preview.hidden = false;
    document.body.classList.add("files-previewing");
  }

  private hidePreview(): void {
    this.preview.hidden = true;
    this.previewContent.replaceChildren();
    document.body.classList.remove("files-previewing");
  }

  private linkButton(
    label: string,
    icon: string,
    href: string,
  ): HTMLAnchorElement {
    const link = el("a", "files-btn");
    link.href = href;
    const i = el("i", `fas ${icon}`);
    i.setAttribute("aria-hidden", "true");
    link.append(i, el("span", "", label));
    return link;
  }

  private sheetAction(
    label: string,
    icon: string,
    run: () => void,
    danger = false,
  ): HTMLButtonElement {
    const button = el(
      "button",
      `files-sheet-action${danger ? " is-danger" : ""}`,
    );
    button.type = "button";
    const i = el("i", `fas ${icon}`);
    i.setAttribute("aria-hidden", "true");
    button.append(i, el("span", "", label));
    button.addEventListener("click", run);
    return button;
  }

  private openSheet(title: string, nodes: HTMLElement[]): void {
    this.sheetTitle.textContent = title;
    this.sheetBody.replaceChildren(...nodes);
    this.backdrop.hidden = false;
    const focusable =
      this.sheetBody.querySelector<HTMLElement>("input, button, a");
    focusable?.focus();
  }

  private closeSheet(): void {
    this.backdrop.hidden = true;
    this.sheetBody.replaceChildren();
  }

  private showActions(entry: Entry): void {
    const nodes: HTMLElement[] = [
      this.sheetAction(
        this.t("open"),
        entry.is_dir ? "fa-folder-open" : "fa-eye",
        () => {
          this.closeSheet();
          this.open(entry);
        },
      ),
    ];
    if (entry.project_url) {
      nodes.push(
        this.sheetAction(
          this.t("openInProject"),
          "fa-up-right-from-square",
          () => {
            window.location.href = entry.project_url;
          },
        ),
      );
    }
    if (!entry.is_dir) {
      nodes.push(
        this.sheetAction(this.t("download"), "fa-download", () => {
          this.closeSheet();
          window.location.href = `${API}download/${query(entry.path)}`;
        }),
      );
    }
    nodes.push(
      this.sheetAction(this.t("rename"), "fa-pen", () =>
        this.askText(this.t("renamePrompt"), entry.name, (name) =>
          this.post("rename", { path: entry.path, name }),
        ),
      ),
      this.sheetAction(this.t("move"), "fa-arrow-right-to-bracket", () =>
        this.askText(this.t("movePrompt"), this.current, (dest) =>
          this.post("move", { path: entry.path, dest }),
        ),
      ),
      this.sheetAction(
        this.t("delete"),
        "fa-trash",
        () => this.confirmDelete(entry),
        true,
      ),
      this.sheetAction(this.t("cancel"), "fa-xmark", () => this.closeSheet()),
    );
    this.openSheet(entry.name, nodes);
  }

  private askText(
    title: string,
    initial: string,
    run: (value: string) => Promise<unknown>,
  ): void {
    const form = el("form", "files-sheet-form");
    const input = el("input", "files-sheet-input");
    input.type = "text";
    input.value = initial;
    input.setAttribute("aria-label", title);
    const row = el("div", "files-sheet-buttons");
    const cancel = el("button", "files-btn", this.t("cancel"));
    cancel.type = "button";
    cancel.addEventListener("click", () => this.closeSheet());
    const ok = el("button", "files-btn files-btn-primary", "OK");
    ok.type = "submit";
    row.append(cancel, ok);
    form.append(input, row);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      run(input.value.trim())
        .then(() => {
          this.closeSheet();
          this.setStatus("");
          return this.load(this.current, false);
        })
        .catch((error) => this.fail(error));
    });
    this.openSheet(title, [form]);
    input.select();
  }

  private confirmDelete(entry: Entry): void {
    const message = el(
      "p",
      "files-sheet-message",
      fmt(this.t("deleteConfirm"), { name: entry.name }),
    );
    const row = el("div", "files-sheet-buttons");
    const cancel = el("button", "files-btn", this.t("cancel"));
    cancel.type = "button";
    cancel.addEventListener("click", () => this.closeSheet());
    const remove = el("button", "files-btn files-btn-danger", this.t("delete"));
    remove.type = "button";
    remove.addEventListener("click", () => {
      this.post("delete", { path: entry.path })
        .then(() => {
          this.closeSheet();
          this.hidePreview();
          return this.load(this.current, false);
        })
        .catch((error) => this.fail(error));
    });
    row.append(cancel, remove);
    this.openSheet(entry.name, [message, row]);
  }

  private async upload(files: FileList | File[]): Promise<void> {
    const list = Array.from(files);
    if (list.length === 0) return;
    const form = new FormData();
    form.append("path", this.current);
    list.forEach((file) => form.append("files", file));
    this.setStatus(this.t("uploading"));
    try {
      const data = await this.request(`${API}api/upload/`, {
        method: "POST",
        body: form,
      });
      this.setStatus(fmt(this.t("uploaded"), { count: data.saved.length }));
      await this.load(this.current, false);
    } catch (error) {
      this.fail(error);
    }
  }

  private bindToolbar(): void {
    const input = byId<HTMLInputElement>("files-upload-input");
    input.addEventListener("change", () => {
      if (input.files) void this.upload(input.files);
      input.value = "";
    });
    byId("files-new-folder").addEventListener("click", () =>
      this.askText(this.t("newFolderPrompt"), "", (name) =>
        this.post("mkdir", { path: this.current, name }),
      ),
    );
    document.querySelectorAll<HTMLElement>(".files-place").forEach((place) => {
      place.addEventListener(
        "click",
        () => void this.load(place.dataset.path || ""),
      );
    });
    byId("files-preview-close").addEventListener("click", () =>
      this.hidePreview(),
    );
    this.backdrop.addEventListener("click", (event) => {
      if (event.target === this.backdrop) this.closeSheet();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!this.backdrop.hidden) this.closeSheet();
      else if (!this.preview.hidden) this.hidePreview();
    });
  }

  private bindDragAndDrop(): void {
    const app = byId("files-app");
    const hint = byId("files-drop-hint");
    let depth = 0;
    app.addEventListener("dragenter", (event) => {
      if (!event.dataTransfer?.types.includes("Files")) return;
      depth += 1;
      hint.hidden = false;
    });
    app.addEventListener("dragleave", () => {
      depth = Math.max(0, depth - 1);
      if (depth === 0) hint.hidden = true;
    });
    app.addEventListener("dragover", (event) => event.preventDefault());
    app.addEventListener("drop", (event) => {
      event.preventDefault();
      depth = 0;
      hint.hidden = true;
      if (event.dataTransfer?.files) void this.upload(event.dataTransfer.files);
    });
  }
}

function boot(): void {
  if (document.getElementById("files-app")) new FilesApp().start();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
