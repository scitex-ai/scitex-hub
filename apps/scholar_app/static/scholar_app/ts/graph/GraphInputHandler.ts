/**
 * GraphInputHandler - Manages the three input modes for citation graph
 *
 * Modes: DOI (direct), Search (by query), Library (from saved papers)
 * Each mode resolves to a DOI which is then used to build the graph.
 */

import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "../../../../../../static/shared/ts/components/inspiring-spinner";

export interface GraphInputCallbacks {
  onDoiSelected: (doi: string) => void;
  onBuildGraph: (doi: string) => void;
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

  private async handleSearchQuery(): Promise<void> {
    const input = document.getElementById(
      "graphSearchInput",
    ) as HTMLInputElement;
    const resultsEl = document.getElementById("graphSearchResults");
    if (!input?.value || !resultsEl) return;

    const query = input.value.trim();
    resultsEl.classList.remove("hidden");
    resultsEl.innerHTML = "";
    this.searchSpinner = startInspiringSpinner(
      resultsEl,
      "Searching for papers...",
    );

    try {
      const response = await fetch(
        `/scholar/api/search/?q=${encodeURIComponent(query)}&limit=5`,
      );
      if (!response.ok) throw new Error("Search failed");
      const data = await response.json();
      const papers = data.results || data.papers || [];

      if (papers.length === 0) {
        this.searchSpinner?.stop();
        this.searchSpinner = null;
        resultsEl.innerHTML = '<p class="empty-message">No papers found</p>';
        return;
      }

      // Find first paper with a DOI
      const paperWithDoi = papers.find(
        (p: { doi?: string }) => p.doi && p.doi.trim(),
      );
      if (!paperWithDoi?.doi) {
        this.searchSpinner?.stop();
        this.searchSpinner = null;
        resultsEl.innerHTML =
          '<p class="empty-message">No papers with DOI found</p>';
        return;
      }

      // Auto-build graph from best match — no cards
      this.searchSpinner?.updateMessage(
        `Found ${papers.length} papers. Building citation network...`,
      );

      // Clean up spinner before handing off to graph builder
      this.searchSpinner?.stop();
      this.searchSpinner = null;
      resultsEl.classList.add("hidden");

      // Fill DOI and trigger graph build
      const doiInput = document.getElementById("doiInput") as HTMLInputElement;
      if (doiInput) doiInput.value = paperWithDoi.doi;
      this.callbacks.onBuildGraph(paperWithDoi.doi);
    } catch {
      this.searchSpinner?.stop();
      this.searchSpinner = null;
      resultsEl.innerHTML = '<p class="error-message">Search failed</p>';
    }
  }

  private async loadLibraryPapers(): Promise<void> {
    const listEl = document.getElementById("graphLibraryList");
    if (!listEl) return;

    listEl.innerHTML = "";
    this.librarySpinner = startInspiringSpinner(listEl, "Loading library...");

    try {
      const response = await fetch("/scholar/api/library/papers/", {
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
    // Fill DOI input and switch to DOI tab
    const doiInput = document.getElementById("doiInput") as HTMLInputElement;
    if (doiInput) doiInput.value = doi;

    document
      .querySelector('.graph-input-tab[data-input-mode="doi"]')
      ?.dispatchEvent(new Event("click"));

    this.callbacks.onDoiSelected(doi);
  }
}
