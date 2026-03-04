/**
 * Swarm Plot Visualization for SciTeX Scholar Filters
 *
 * Creates interactive swarm plots using Plotly.ts to visualize the distribution of papers
 * across Year, Citations, and Impact Factor dimensions. Syncs with result cards.
 *
 * External library: Plotly.ts (requires `any` types or @ts-ignore)
 *
 * @version 2.0.0
 */

// @ts-ignore - Plotly library types

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/search/swarm-plots.ts loaded",
);
declare const Plotly: any;

import {
  renderYearSwarmPlot,
  renderCitationsSwarmPlot,
  renderImpactFactorSwarmPlot,
} from "./_swarm-plot-renderers";

/**
 * Paper data interface
 */
interface PaperData {
  id?: string;
  title?: string;
  year?: number;
  citations?: number;
  impact_factor?: number;
  journal?: string;
  authors?: string;
}

/**
 * Swarm plot configuration
 */
interface SwarmConfig {
  height: number;
  includedColor: string;
  filteredColor: string;
  pointSize: number;
  hovertemplate: string;
}

/**
 * Current filter ranges (synced with sliders)
 */
interface FilterRanges {
  year: [number, number] | null;
  citations: [number, number] | null;
  impactFactor: [number, number] | null;
}

/**
 * Swarm Plots module using object literal pattern
 */
const SwarmPlots = {
  config: {
    height: 60,
    includedColor: "#3b82f6",
    filteredColor: "#d1d5db",
    pointSize: 6,
    hovertemplate: "%{text}<extra></extra>",
  } as SwarmConfig,

  data: [] as PaperData[],
  filteredIndices: new Set<number>(),

  // Store consistent jitter values so plots don't jump around
  jitterCache: new Map<number, number>(),

  // Current filter ranges for dynamic axis
  currentRanges: {
    year: null,
    citations: null,
    impactFactor: null,
  } as FilterRanges,

  /**
   * Get or create jitter value for an index
   */
  getJitter: function (idx: number): number {
    if (!this.jitterCache.has(idx)) {
      this.jitterCache.set(idx, Math.random() * 0.8 + 0.1);
    }
    return this.jitterCache.get(idx)!;
  },

  /**
   * Initialize swarm plots with paper data.
   * Lazy-loads Plotly.ts (~3.5MB) only when actually needed.
   */
  init: function (papers: PaperData[]): void {
    console.log("[SwarmPlots] Initializing with", papers.length, "papers");
    this.data = papers;
    this.filteredIndices.clear();
    this.jitterCache.clear();

    const self = this;

    function doInit(): void {
      if (typeof Plotly === "undefined") {
        console.warn(
          "[SwarmPlots] Plotly.ts not available, skipping visualization",
        );
        return;
      }
      self.renderAllPlots();

      // Listen for theme changes
      const observer = new MutationObserver(() => {
        self.renderAllPlots();
      });
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    // Lazy-load Plotly if not yet loaded
    if (typeof Plotly !== "undefined") {
      doInit();
    } else if (typeof (window as any).loadPlotly === "function") {
      (window as any)
        .loadPlotly()
        .then(() => doInit())
        .catch((err: Error) =>
          console.warn("[SwarmPlots] Failed to load Plotly:", err.message),
        );
    } else {
      console.warn("[SwarmPlots] No Plotly loader available, skipping");
    }
  },

  /**
   * Render all three swarm plots using extracted renderer functions
   */
  renderAllPlots: function (): void {
    if (typeof Plotly === "undefined") return;
    const ctx = {
      data: this.data,
      filteredIndices: this.filteredIndices,
      jitterCache: this.jitterCache,
      config: this.config,
      currentRanges: this.currentRanges,
      getJitter: (idx: number) => this.getJitter(idx),
    };
    renderYearSwarmPlot(ctx);
    renderCitationsSwarmPlot(ctx);
    renderImpactFactorSwarmPlot(ctx);
  },

  /**
   * Update plots when filters change - syncs with slider values
   */
  updateFilter: function (
    yearRange: [number, number] | null,
    citationsRange: [number, number] | null,
    impactRange: [number, number] | null,
  ): void {
    // Store current ranges for dynamic axis
    this.currentRanges.year = yearRange;
    this.currentRanges.citations = citationsRange;
    this.currentRanges.impactFactor = impactRange;

    this.filteredIndices.clear();

    this.data.forEach((paper, idx) => {
      let filtered = false;

      // Year filter
      if (yearRange && paper.year) {
        if (paper.year < yearRange[0] || paper.year > yearRange[1]) {
          filtered = true;
        }
      }

      // Citations filter
      if (citationsRange && paper.citations !== undefined) {
        if (
          paper.citations < citationsRange[0] ||
          paper.citations > citationsRange[1]
        ) {
          filtered = true;
        }
      }

      // Impact factor filter
      if (impactRange && paper.impact_factor !== undefined) {
        if (
          paper.impact_factor < impactRange[0] ||
          paper.impact_factor > impactRange[1]
        ) {
          filtered = true;
        }
      }

      if (filtered) {
        this.filteredIndices.add(idx);
      }
    });

    // Re-render all plots with updated colors
    this.renderAllPlots();

    // Update result cards in main panel using data attributes
    this.updateResultCards();

    console.log(
      "[SwarmPlots] Filters updated,",
      this.filteredIndices.size,
      "papers filtered out",
    );
  },

  /**
   * Update result cards to show filtered state using data attributes
   */
  updateResultCards: function (): void {
    const cards = document.querySelectorAll(
      ".result-card, .result-card-compact",
    ) as NodeListOf<HTMLElement>;

    let filteredCount = 0;

    cards.forEach((card) => {
      // Get filter criteria from data attributes
      const cardYear = parseInt(card.dataset.year || "0");
      const cardCitations = parseInt(card.dataset.citations || "0");
      const cardIF = parseFloat(card.dataset.impactFactor || "0");

      let isFiltered = false;

      // Check year range
      if (this.currentRanges.year) {
        const [minYear, maxYear] = this.currentRanges.year;
        if (cardYear > 0 && (cardYear < minYear || cardYear > maxYear)) {
          isFiltered = true;
        }
      }

      // Check citations range
      if (this.currentRanges.citations && !isFiltered) {
        const [minCitations, maxCitations] = this.currentRanges.citations;
        if (cardCitations < minCitations || cardCitations > maxCitations) {
          isFiltered = true;
        }
      }

      // Check impact factor range
      if (this.currentRanges.impactFactor && !isFiltered) {
        const [minIF, maxIF] = this.currentRanges.impactFactor;
        if (cardIF < minIF || cardIF > maxIF) {
          isFiltered = true;
        }
      }

      if (isFiltered) {
        card.classList.add("result-card-filtered");
        filteredCount++;
      } else {
        card.classList.remove("result-card-filtered");
      }
    });

    // Update result count display
    const countEl = document.getElementById("searchResultsText");
    if (countEl) {
      const totalCards = cards.length;
      const visibleCards = totalCards - filteredCount;
      const originalText =
        countEl.getAttribute("data-original-text") || countEl.textContent || "";

      if (!countEl.getAttribute("data-original-text")) {
        countEl.setAttribute("data-original-text", originalText);
      }

      if (filteredCount > 0) {
        countEl.textContent = `${visibleCards} of ${totalCards} results shown`;
      } else {
        countEl.textContent = originalText;
      }
    }
  },

  /**
   * Reset all filters
   */
  resetFilters: function (): void {
    this.filteredIndices.clear();
    this.currentRanges = {
      year: null,
      citations: null,
      impactFactor: null,
    };

    this.renderAllPlots();

    // Clear filtered state from all cards
    document.querySelectorAll(".result-card-filtered").forEach((card) => {
      card.classList.remove("result-card-filtered");
    });

    // Reset result count
    const countEl = document.getElementById("searchResultsText");
    if (countEl) {
      const originalText = countEl.getAttribute("data-original-text");
      if (originalText) {
        countEl.textContent = originalText;
      }
    }

    console.log("[SwarmPlots] Filters reset");
  },
};

// Expose to global scope
(window as any).SwarmPlots = SwarmPlots;

// Auto-initialize if paper data is available
function initSwarmPlots(): void {
  const paperDataElement = document.getElementById(
    "paperData",
  ) as HTMLElement | null;
  if (paperDataElement && paperDataElement.textContent) {
    try {
      const papers = JSON.parse(paperDataElement.textContent) as PaperData[];
      SwarmPlots.init(papers);
    } catch (e: any) {
      console.warn("[SwarmPlots] Failed to parse paper data:", e.message);
    }
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initSwarmPlots();
  });
} else {
  initSwarmPlots();
}
