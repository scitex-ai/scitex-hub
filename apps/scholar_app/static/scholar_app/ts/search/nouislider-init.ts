/**
 * noUiSlider Initialization for SciTeX Scholar Filters
 *
 * This file initializes dual-range sliders using the noUiSlider library for filtering
 * scholarly papers by year, citations, and impact factor. The sliders read their initial
 * values from URL parameters and update hidden form inputs when changed.
 * Now integrated with SwarmPlots for visual filtering.
 *
 * External library: noUiSlider (requires `any` types or @ts-ignore)
 *
 * @version 2.0.0
 */

// @ts-ignore - noUiSlider library types

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/search/nouislider-init.ts loaded",
);
declare const noUiSlider: any;

/**
 * Extended HTMLElement interface for noUiSlider
 */
interface NoUiSliderElement extends HTMLElement {
  noUiSlider?: any;
}

/**
 * Window interface extension for initialization guard
 */
declare global {
  interface Window {
    __nouisliderInitialized?: boolean;
    SwarmPlots?: {
      updateFilter: (
        yearRange: [number, number] | null,
        citationsRange: [number, number] | null,
        impactRange: [number, number] | null
      ) => void;
      init: (data: any[]) => void;
      resetFilters: () => void;
    };
  }
}

// Export to make this an ES module
export {};

// Current filter values (for syncing across sliders)
let currentYearRange: [number, number] | null = null;
let currentCitationsRange: [number, number] | null = null;
let currentImpactRange: [number, number] | null = null;

/**
 * Notify SwarmPlots of filter changes (debounced)
 */
let updateTimeout: number | null = null;
function notifySwarmPlots(): void {
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }
  updateTimeout = window.setTimeout(() => {
    if (window.SwarmPlots && typeof window.SwarmPlots.updateFilter === 'function') {
      window.SwarmPlots.updateFilter(
        currentYearRange,
        currentCitationsRange,
        currentImpactRange
      );
    }
  }, 100); // 100ms debounce
}

// Guard against multiple initializations
if (window.__nouisliderInitialized) {
  console.log("[noUiSlider] Already initialized, skipping");
} else {
  window.__nouisliderInitialized = true;
  document.addEventListener("DOMContentLoaded", function () {
    console.log("[noUiSlider] Initializing dual-range sliders...");

    // Get URL parameters for initial values
    const urlParams = new URLSearchParams(window.location.search);

    // ============================================
    // Year Slider (dynamic range from data attributes)
    // ============================================
    const yearSlider = document.getElementById(
      "yearSlider",
    ) as NoUiSliderElement | null;
    if (yearSlider && !yearSlider.noUiSlider) {
      try {
        const yearMinRange = parseInt(yearSlider.dataset.min || "1900");
        const yearMaxRange = parseInt(yearSlider.dataset.max || "2025");
        const yearMin =
          parseInt(urlParams.get("year_from") || "") || yearMinRange;
        const yearMax =
          parseInt(urlParams.get("year_to") || "") || yearMaxRange;

        // @ts-ignore - noUiSlider library
        noUiSlider.create(yearSlider, {
          start: [yearMin, yearMax],
          connect: true,
          range: {
            min: yearMinRange,
            max: yearMaxRange,
          },
          step: 1,
          format: {
            to: function (value: number): number {
              return Math.round(value);
            },
            from: function (value: number): number {
              return Math.round(value);
            },
          },
        });

        // Sync slider to hidden inputs and display badges
        yearSlider.noUiSlider.on(
          "update",
          function (values: string[], handle: number): void {
            const minValue = parseInt(values[0]);
            const maxValue = parseInt(values[1]);

            const yearFromInput = document.getElementById(
              "yearFromInput",
            ) as HTMLInputElement | null;
            const yearToInput = document.getElementById(
              "yearToInput",
            ) as HTMLInputElement | null;
            const yearMinDisplay = document.getElementById(
              "yearMinDisplay",
            ) as HTMLElement | null;
            const yearMaxDisplay = document.getElementById(
              "yearMaxDisplay",
            ) as HTMLElement | null;

            if (yearFromInput) yearFromInput.value = String(minValue);
            if (yearToInput) yearToInput.value = String(maxValue);
            if (yearMinDisplay) yearMinDisplay.textContent = String(minValue);
            if (yearMaxDisplay) yearMaxDisplay.textContent = String(maxValue);

            // Update SwarmPlots
            currentYearRange = [minValue, maxValue];
            notifySwarmPlots();
          },
        );

        console.log(
          "[noUiSlider] Year slider initialized:",
          yearMin,
          "-",
          yearMax,
          "(range:",
          yearMinRange,
          "-",
          yearMaxRange + ")",
        );
      } catch (e: any) {
        console.warn(
          "[noUiSlider] Year slider initialization error:",
          e.message,
        );
      }
    }

    // ============================================
    // Citations Slider (dynamic max from data attribute)
    // ============================================
    const citationsSlider = document.getElementById(
      "citationsSlider",
    ) as NoUiSliderElement | null;
    if (citationsSlider && !citationsSlider.noUiSlider) {
      try {
        const citationsMin =
          parseInt(urlParams.get("min_citations") || "0") || 0;
        const citationsMaxRange =
          parseInt(citationsSlider.dataset.max || "12000") || 12000;
        const citationsMax =
          parseInt(urlParams.get("max_citations") || "") || citationsMaxRange;

        // @ts-ignore - noUiSlider library
        noUiSlider.create(citationsSlider, {
          start: [citationsMin, citationsMax],
          connect: true,
          range: {
            min: 0,
            max: citationsMaxRange,
          },
          step: Math.max(1, Math.floor(citationsMaxRange / 100)),
          format: {
            to: function (value: number): number {
              return Math.round(value);
            },
            from: function (value: number): number {
              return Math.round(value);
            },
          },
        });

        // Sync slider to hidden inputs and display badges
        citationsSlider.noUiSlider.on(
          "update",
          function (values: string[], handle: number): void {
            const minValue = parseInt(values[0]);
            const maxValue = parseInt(values[1]);

            const citationsMinInput = document.getElementById(
              "citationsMinInput",
            ) as HTMLInputElement | null;
            const citationsMaxInput = document.getElementById(
              "citationsMaxInput",
            ) as HTMLInputElement | null;
            const citationsMinDisplay = document.getElementById(
              "citationsMinDisplay",
            ) as HTMLElement | null;
            const citationsMaxDisplay = document.getElementById(
              "citationsMaxDisplay",
            ) as HTMLElement | null;

            if (citationsMinInput) citationsMinInput.value = String(minValue);
            if (citationsMaxInput) citationsMaxInput.value = String(maxValue);
            if (citationsMinDisplay) citationsMinDisplay.textContent = String(minValue);
            if (citationsMaxDisplay) citationsMaxDisplay.textContent = String(maxValue);

            // Update SwarmPlots
            currentCitationsRange = [minValue, maxValue];
            notifySwarmPlots();
          },
        );

        console.log(
          "[noUiSlider] Citations slider initialized:",
          citationsMin,
          "-",
          citationsMax,
          "(max range:",
          citationsMaxRange + ")",
        );
      } catch (e: any) {
        console.warn(
          "[noUiSlider] Citations slider initialization error:",
          e.message,
        );
      }
    }

    // ============================================
    // Impact Factor Slider (dynamic max from data attribute, decimals)
    // ============================================
    const impactFactorSlider = document.getElementById(
      "impactFactorSlider",
    ) as NoUiSliderElement | null;
    if (impactFactorSlider && !impactFactorSlider.noUiSlider) {
      try {
        const impactMin =
          parseFloat(urlParams.get("min_impact_factor") || "0") || 0;
        const impactMaxRange =
          parseFloat(impactFactorSlider.dataset.max || "50.0") || 50.0;
        const impactMax =
          parseFloat(urlParams.get("max_impact_factor") || "") ||
          impactMaxRange;

        // @ts-ignore - noUiSlider library
        noUiSlider.create(impactFactorSlider, {
          start: [impactMin, impactMax],
          connect: true,
          range: {
            min: 0,
            max: impactMaxRange,
          },
          step: Math.max(0.1, impactMaxRange / 100),
          format: {
            to: function (value: number): string {
              return value.toFixed(1);
            },
            from: function (value: string): number {
              return parseFloat(value);
            },
          },
        });

        // Sync slider to hidden inputs and display badges
        impactFactorSlider.noUiSlider.on(
          "update",
          function (values: string[], handle: number): void {
            const minValue = parseFloat(values[0]);
            const maxValue = parseFloat(values[1]);

            const impactFactorMinInput = document.getElementById(
              "impactFactorMinInput",
            ) as HTMLInputElement | null;
            const impactFactorMaxInput = document.getElementById(
              "impactFactorMaxInput",
            ) as HTMLInputElement | null;
            const impactFactorMinDisplay = document.getElementById(
              "impactFactorMinDisplay",
            ) as HTMLElement | null;
            const impactFactorMaxDisplay = document.getElementById(
              "impactFactorMaxDisplay",
            ) as HTMLElement | null;

            if (impactFactorMinInput) impactFactorMinInput.value = values[0];
            if (impactFactorMaxInput) impactFactorMaxInput.value = values[1];
            if (impactFactorMinDisplay)
              impactFactorMinDisplay.textContent = values[0];
            if (impactFactorMaxDisplay)
              impactFactorMaxDisplay.textContent = values[1];

            // Update SwarmPlots
            currentImpactRange = [minValue, maxValue];
            notifySwarmPlots();
          },
        );

        console.log(
          "[noUiSlider] Impact Factor slider initialized:",
          impactMin,
          "-",
          impactMax,
          "(max range:",
          impactMaxRange + ")",
        );
      } catch (e: any) {
        console.warn(
          "[noUiSlider] Impact Factor slider initialization error:",
          e.message,
        );
      }
    }

    console.log(
      "[noUiSlider] All sliders initialized successfully with dynamic ranges",
    );
  });
}
