/**
 * GraphInputHandler - Manages input modes for citation graph
 *
 * Modes: Search (by query/DOI), Library (from saved papers)
 * Search delegates to backend which handles DOI detection + graph building.
 */

import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "../../../../../../static/shared/ts/components/inspiring-spinner";

export interface GraphInputCallbacks {
  onBuildGraph: (dois: string[]) => void;
  onBuildFromQuery: (query: string) => void;
  escapeHtml: (text: string) => string;
}

export class GraphInputHandler {
  private callbacks: GraphInputCallbacks;
  private searchSpinner: SpinnerHandle | null = null;
  private librarySpinner: SpinnerHandle | null = null;

  constructor(callbacks: GraphInputCallbacks) {
    this.callbacks = callbacks;
    this.bindEvents();
  }

  private bindEvents(): void {
    // Input mode tabs (DOI / Search / Library)
    document.querySelectorAll(".graph-input-tab").forEach((tab) => {
      tab.addEventListener("click", (e) => {
        e.preventDefault();
        const mode = tab.getAttribute("data-input-mode");
        if (!mode) return;
        document
          .querySelectorAll(".graph-input-tab")
          .forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        document
          .querySelectorAll(".graph-input-panel")
          .forEach((p) => p.classList.add("hidden"));
        const panelId = `graphInput${mode.charAt(0).toUpperCase() + mode.slice(1)}`;
        document.getElementById(panelId)?.classList.remove("hidden");
        if (mode === "library") this.loadLibraryPapers();
      });
    });

    // Search button
    document
      .getElementById("graphSearchBtn")
      ?.addEventListener("click", () => this.handleSearchQuery());
    document
      .getElementById("graphSearchInput")
      ?.addEventListener("keydown", (e) => {
        if ((e as KeyboardEvent).key === "Enter") {
          e.preventDefault();
          this.handleSearchQuery();
        }
      });
  }

  private handleSearchQuery(): void {
    const input = document.getElementById(
      "graphSearchInput",
    ) as HTMLInputElement;
    const resultsEl = document.getElementById("graphSearchResults");
    if (!input?.value || !resultsEl) return;

    const query = input.value.trim();
    resultsEl.classList.add("hidden");

    // Delegate entirely to backend — search, DOI detection, graph building
    this.callbacks.onBuildFromQuery(query);
  }

  private async loadLibraryPapers(): Promise<void> {
    const listEl = document.getElementById("graphLibraryList");
    if (!listEl) return;

    listEl.innerHTML = "";
    this.librarySpinner = startInspiringSpinner(listEl, "Loading library...");

    try {
      const response = await fetch("/apps/scholar/api/library/papers/", {
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error("Failed to load library");
      const data = await response.json();
      const papers = data.papers || [];

      this.librarySpinner?.stop();
      this.librarySpinner = null;

      if (papers.length === 0) {
        listEl.innerHTML =
          '<p class="empty-message">No papers in library. Add papers from Search or import BibTeX.</p>';
        return;
      }

      listEl.innerHTML = papers
        .filter((p: { doi?: string }) => p.doi)
        .map(
          (p: {
            doi?: string;
            title?: string;
            authors?: string;
            year?: number;
          }) => `
          <div class="graph-library-item" data-doi="${p.doi}">
            <div class="graph-library-item__title">${this.callbacks.escapeHtml(p.title || "Untitled")}</div>
            <div class="graph-library-item__meta">${p.authors || ""} (${p.year || "?"})</div>
          </div>
        `,
        )
        .join("");

      listEl.querySelectorAll(".graph-library-item").forEach((item) => {
        item.addEventListener("click", () => {
          const doi = item.getAttribute("data-doi");
          if (doi) this.selectDoi(doi);
        });
      });
    } catch {
      this.librarySpinner?.stop();
      this.librarySpinner = null;
      listEl.innerHTML = '<p class="error-message">Failed to load library</p>';
    }
  }

  private selectDoi(doi: string): void {
    // Build graph directly from library-selected DOI
    this.callbacks.onBuildGraph([doi]);
  }
}
