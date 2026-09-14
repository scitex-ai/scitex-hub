/**
 * Slides — Markdown deck editor with a live slide preview.
 * A deck is slides/<name>.md in the project; "---" on its own line separates slides.
 */
import { getCsrfToken } from "@/utils/csrf";

declare const marked: { parse(src: string): string } | undefined;
declare const DOMPurify: { sanitize(html: string): string } | undefined;

const API = "/apps/slides/api";

interface DecksResponse {
  success: boolean;
  decks: string[];
  figures: string[];
  can_edit: boolean;
}

const FRONT_MATTER = /^---\s*\n[\s\S]*?\n---\s*(\n|$)/;

export function splitSlides(source: string): string[] {
  const body = source.replace(/\r\n/g, "\n").replace(FRONT_MATTER, "");
  return body
    .split(/\n-{3,}\s*\n/)
    .map((s) => s.trim())
    .filter((s, i, all) => s.length > 0 || all.length === 1);
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(src: string): string {
  if (typeof marked === "undefined") {
    return `<pre>${escapeHtml(src)}</pre>`;
  }
  const html = marked.parse(src);
  return typeof DOMPurify === "undefined"
    ? escapeHtml(src)
    : DOMPurify.sanitize(html);
}

/** Resolve an image src written relative to slides/<deck>.md to a project path. */
export function projectPathFor(src: string): string | null {
  if (/^([a-z]+:|\/\/|\/|data:|#)/i.test(src)) return null;
  const parts = ["slides"];
  for (const segment of src.split("/")) {
    if (segment === "" || segment === ".") continue;
    if (segment === "..") {
      if (!parts.length) return null;
      parts.pop();
    } else {
      parts.push(segment);
    }
  }
  return parts.join("/");
}

class SlidesApp {
  private root: HTMLElement;
  private project: string;
  private canEdit: boolean;
  private source: HTMLTextAreaElement;
  private preview: HTMLElement;
  private select: HTMLSelectElement;
  private status: HTMLElement;
  private figures: string[] = [];
  private deck = "";
  private dirty = false;
  private renderTimer = 0;

  constructor(root: HTMLElement) {
    this.root = root;
    this.project = root.dataset.project || "";
    this.canEdit = root.dataset.canEdit === "true";
    this.source = root.querySelector("#slides-source") as HTMLTextAreaElement;
    this.preview = root.querySelector("#slides-preview") as HTMLElement;
    this.select = root.querySelector(
      "#slides-deck-select",
    ) as HTMLSelectElement;
    this.status = root.querySelector("#slides-status") as HTMLElement;
  }

  private t(key: string): string {
    return this.root.dataset[key] || "";
  }

  private fileUrl(path: string): string {
    const q = new URLSearchParams({ project: this.project, path });
    return `${API}/file/?${q}`;
  }

  async start(): Promise<void> {
    this.bind();
    const data = await this.getJson<DecksResponse>(
      `${API}/decks/?${new URLSearchParams({ project: this.project })}`,
    );
    this.figures = data.figures;
    this.fillDecks(data.decks);
    const wanted = new URLSearchParams(location.search).get("deck");
    const first =
      wanted && data.decks.includes(wanted) ? wanted : data.decks[0];
    if (first) {
      await this.openDeck(first);
    } else {
      this.setStatus(
        this.canEdit ? this.t("i18nEmpty") : this.t("i18nReadOnly"),
      );
      this.render();
    }
  }

  private bind(): void {
    this.source.addEventListener("input", () => {
      this.markDirty(true);
      window.clearTimeout(this.renderTimer);
      this.renderTimer = window.setTimeout(() => this.render(), 150);
    });
    this.select.addEventListener("change", () =>
      this.openDeck(this.select.value),
    );
    this.root.addEventListener("click", (event) => {
      const target = (event.target as HTMLElement).closest<HTMLElement>(
        "[data-action], [data-view-tab]",
      );
      if (!target) return;
      if (target.dataset.viewTab) return this.setView(target.dataset.viewTab);
      void this.run(target.dataset.action || "");
    });
    document.addEventListener("keydown", (event) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key === "s" &&
        this.canEdit
      ) {
        event.preventDefault();
        void this.save();
      }
    });
    window.addEventListener("beforeunload", (event) => {
      if (this.dirty) event.preventDefault();
    });
  }

  private async run(action: string): Promise<void> {
    if (action === "save") return this.save();
    if (action === "new-deck") return this.newDeck();
    if (action === "deck-from-project") return this.deckFromProject();
    if (action === "insert-figure") return this.openFigurePicker();
    if (action === "export-pdf") return this.exportPdf();
  }

  private setView(view: string): void {
    this.root.dataset.view = view;
    this.root
      .querySelectorAll<HTMLElement>("[data-view-tab]")
      .forEach((tab) => {
        tab.setAttribute("aria-selected", String(tab.dataset.viewTab === view));
      });
    if (view === "editor") this.source.focus();
  }

  private fillDecks(decks: string[]): void {
    this.select.replaceChildren(
      ...decks.map((name) => new Option(`${name}.md`, name)),
    );
    this.select.hidden = decks.length === 0;
  }

  private async openDeck(name: string): Promise<void> {
    const q = new URLSearchParams({ project: this.project, name });
    const data = await this.getJson<{ content: string }>(`${API}/deck/?${q}`);
    this.deck = name;
    this.select.value = name;
    this.source.value = data.content;
    this.markDirty(false);
    this.render();
    const url = new URL(location.href);
    url.searchParams.set("deck", name);
    history.replaceState(null, "", url);
  }

  private render(): void {
    const slides = splitSlides(this.source.value);
    this.preview.replaceChildren(
      ...slides.map((md, index) => {
        const slide = document.createElement("article");
        slide.className = "slide";
        slide.setAttribute("aria-label", `${index + 1} / ${slides.length}`);
        slide.innerHTML = `<div class="slide-inner">${renderMarkdown(md)}</div><span class="slide-number">${index + 1}</span>`;
        slide.querySelectorAll("img").forEach((img) => {
          const path = projectPathFor(img.getAttribute("src") || "");
          if (path) img.src = this.fileUrl(path);
        });
        return slide;
      }),
    );
  }

  private markDirty(dirty: boolean): void {
    this.dirty = dirty;
    this.setStatus(
      dirty ? this.t("i18nUnsaved") : this.deck ? this.t("i18nSaved") : "",
    );
  }

  private setStatus(text: string): void {
    this.status.textContent = text;
  }

  private async save(): Promise<void> {
    if (!this.deck) return this.newDeck();
    try {
      await this.postJson(`${API}/deck/`, {
        project: this.project,
        name: this.deck,
        content: this.source.value,
      });
      this.markDirty(false);
    } catch {
      this.setStatus(this.t("i18nSaveFailed"));
    }
  }

  private async newDeck(): Promise<void> {
    const name = window.prompt(this.t("i18nDeckName"), "talk");
    if (!name) return;
    const content =
      this.source.value.trim() && !this.deck
        ? this.source.value
        : `# ${name}\n\n---\n\n## \n`;
    const data = await this.postJson<{ name: string }>(`${API}/deck/`, {
      project: this.project,
      name,
      content,
    });
    await this.refreshDecks();
    await this.openDeck(data.name);
    this.setView("editor");
  }

  private async deckFromProject(): Promise<void> {
    const data = await this.postJson<{ name: string }>(
      `${API}/deck/from-project/`,
      {
        project: this.project,
      },
    );
    await this.refreshDecks();
    await this.openDeck(data.name);
  }

  private async refreshDecks(): Promise<void> {
    const data = await this.getJson<DecksResponse>(
      `${API}/decks/?${new URLSearchParams({ project: this.project })}`,
    );
    this.figures = data.figures;
    this.fillDecks(data.decks);
  }

  private openFigurePicker(): void {
    const dialog = this.root.querySelector(
      "#slides-figure-dialog",
    ) as HTMLDialogElement;
    const list = this.root.querySelector("#slides-figure-list") as HTMLElement;
    if (!this.figures.length) {
      const empty = document.createElement("li");
      empty.textContent = this.t("i18nNoFigures");
      list.replaceChildren(empty);
    } else {
      list.replaceChildren(
        ...this.figures.map((path) => {
          const item = document.createElement("li");
          const button = document.createElement("button");
          button.type = "button";
          button.className = "slides-figure";
          const img = document.createElement("img");
          img.loading = "lazy";
          img.alt = "";
          img.src = this.fileUrl(path);
          const label = document.createElement("span");
          label.textContent = path;
          button.append(img, label);
          button.addEventListener("click", () => {
            this.insertFigure(path);
            dialog.close();
          });
          item.append(button);
          return item;
        }),
      );
    }
    dialog.showModal();
  }

  private insertFigure(path: string): void {
    const alt = (path.split("/").pop() || "").replace(/\.[^.]+$/, "");
    const snippet = `![${alt}](../${path})`;
    const { selectionStart: start, selectionEnd: end, value } = this.source;
    this.source.value = `${value.slice(0, start)}${snippet}${value.slice(end)}`;
    this.source.selectionStart = this.source.selectionEnd =
      start + snippet.length;
    this.markDirty(true);
    this.render();
  }

  private exportPdf(): void {
    const styles = Array.from(
      document.querySelectorAll<HTMLLinkElement>(
        'link[href*="slides_app/css/slides"]',
      ),
    )
      .map((link) => `<link rel="stylesheet" href="${link.href}">`)
      .join("");
    const win = window.open("", "_blank");
    if (!win) return;
    const title = escapeHtml(this.deck || "slides");
    win.document.write(
      `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title>${styles}</head>` +
        `<body class="slides-print"><div class="slides-deck">${this.preview.innerHTML}</div></body></html>`,
    );
    win.document.close();
    win.addEventListener("load", () => {
      win.focus();
      win.print();
    });
  }

  private async getJson<T>(url: string): Promise<T> {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  }

  private async postJson<T>(url: string, body: object): Promise<T> {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  }
}

function init(): void {
  const root = document.getElementById("slides-app");
  if (!root || !root.dataset.project || root.dataset.slidesReady) return;
  root.dataset.slidesReady = "1";
  new SlidesApp(root).start().catch((err) => console.error("[slides]", err));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
