/**
 * Bottom sheet for a tapped paper: title, year, authors, DOI link,
 * "Add to library" (project bibliography) and "Explore from here".
 */

import type { NetworkNode } from "./types";
import { gt } from "./_graph-i18n";
import { getCsrfToken } from "../common/_scholar-index/utilities";

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function selectedProjectId(): string | null {
  const stored = sessionStorage.getItem("scholar_selected_project_id");
  if (stored) return stored;
  return (
    document.getElementById("scholar-global-config")?.dataset.projectId ?? null
  );
}

async function addToLibrary(
  node: NetworkNode,
  btn: HTMLButtonElement,
): Promise<void> {
  const projectId = selectedProjectId();
  if (!projectId) {
    btn.textContent = gt("noProject");
    return;
  }
  btn.disabled = true;
  btn.textContent = gt("saving");
  const body = new URLSearchParams({
    project_id: projectId,
    title: node.title,
    authors: (node.authors || []).join(", "),
    year: node.year ? String(node.year) : "",
    journal: node.journal || "",
    doi: node.id,
    source: "citation_graph",
    url: `https://doi.org/${node.id}`,
  });
  try {
    const res = await fetch("/apps/scholar/api/save-paper/", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.success) {
      btn.textContent = gt("saved");
      btn.classList.add("is-saved");
      return;
    }
    btn.textContent = gt("saveFailed");
  } catch {
    btn.textContent = gt("saveFailed");
  }
  btn.disabled = false;
}

export class NodeSheet {
  private el: HTMLElement;
  private onExplore: (node: NetworkNode) => void;
  private onClose: () => void;

  constructor(
    el: HTMLElement,
    onExplore: (node: NetworkNode) => void,
    onClose: () => void,
  ) {
    this.el = el;
    this.onExplore = onExplore;
    this.onClose = onClose;
  }

  private isSidePanel(): boolean {
    return window.innerWidth > 768;
  }

  /** Space the sheet covers: bottom on phones, right side on desktop. */
  height(): number {
    if (this.el.classList.contains("hidden") || this.isSidePanel()) return 0;
    return this.el.offsetHeight;
  }

  width(): number {
    if (this.el.classList.contains("hidden") || !this.isSidePanel()) return 0;
    return this.el.offsetWidth + 24;
  }

  hide(): void {
    this.el.classList.add("hidden");
  }

  show(node: NetworkNode): void {
    const authors = node.authors || [];
    const authorText =
      authors.slice(0, 4).join(", ") + (authors.length > 4 ? " et al." : "");
    const meta = [node.year || "", node.journal || ""]
      .filter(Boolean)
      .join(" · ");
    const cites =
      node.citation_count != null
        ? `<span class="cg-sheet__cites">${node.citation_count.toLocaleString()} ${gt("citations")}</span>`
        : "";
    this.el.innerHTML = `
      <div class="cg-sheet__grip" aria-hidden="true"></div>
      <div class="cg-sheet__head">
        <span class="cg-sheet__kind${node.is_seed ? " is-seed" : ""}">${gt(node.is_seed ? "seedPaper" : "citedPaper")}</span>
        ${cites}
        <button type="button" class="cg-sheet__close" aria-label="${gt("close")}">&times;</button>
      </div>
      <h3 class="cg-sheet__title">${escapeHtml(node.title || node.id)}</h3>
      ${meta ? `<div class="cg-sheet__meta">${escapeHtml(String(meta))}</div>` : ""}
      ${authorText ? `<div class="cg-sheet__authors">${escapeHtml(authorText)}</div>` : ""}
      <div class="cg-sheet__actions">
        <a class="cg-sheet__btn" href="https://doi.org/${encodeURI(node.id)}" target="_blank" rel="noopener">
          <i class="fas fa-external-link-alt"></i> ${gt("openDoi")}
        </a>
        <button type="button" class="cg-sheet__btn cg-sheet__btn--primary" data-act="add">
          <i class="fas fa-bookmark"></i> <span>${gt("addToLibrary")}</span>
        </button>
        ${node.is_seed ? "" : `<button type="button" class="cg-sheet__btn" data-act="explore" title="${gt("explore")}"><i class="fas fa-project-diagram"></i> ${gt("exploreShort")}</button>`}
      </div>`;
    this.el.classList.remove("hidden");
    this.el.querySelector(".cg-sheet__close")?.addEventListener("click", () => {
      this.hide();
      this.onClose();
    });
    const add = this.el.querySelector<HTMLButtonElement>('[data-act="add"]');
    add?.addEventListener("click", () => void addToLibrary(node, add));
    this.el
      .querySelector('[data-act="explore"]')
      ?.addEventListener("click", () => this.onExplore(node));
  }
}
