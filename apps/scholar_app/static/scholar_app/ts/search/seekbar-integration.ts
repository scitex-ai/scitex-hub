/**

 * SciTeX Seekbar Integration for Scholar App
 *
 * This file provides integration between the SciTeX Seekbar component
 * and the Scholar app's existing filter system. It can work alongside
 * noUiSlider or replace it entirely.
 *
 * External library: ScitexSeekbar (requires `any` types or @ts-ignore)
 *
 * @version 1.0.0
 */

// @ts-ignore - ScitexSeekbar library types

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/search/seekbar-integration.ts loaded",
);
declare const ScitexSeekbar: any;

/**
 * Seekbar values interface
 */
interface SeekbarValues {
  min: number;
  max: number;
}

/**
 * Seekbar instance interface
 */
interface SeekbarInstance {
  getValues: () => SeekbarValues;
  setValues: (min: number, max: number) => void;
  reset: () => void;
}

/**
 * Extended HTMLElement with noUiSlider property
 */
interface NoUiSliderElement extends HTMLElement {
  noUiSlider?: any;
}

/**
 * Window interface extension
 */
declare global {
  interface Window {
    __scholarSeekbarInitialized?: boolean;
    scholarSeekbar?: ScholarSeekbarIntegration;
  }
}

// Export to make this an ES module
export {};

/**
 * ScholarSeekbarIntegration class
 */
class ScholarSeekbarIntegration {
  private sliders: { [key: string]: SeekbarInstance };

  constructor() {
    this.sliders = {};
    this.init();
  }

  /**
   * Initialize seekbar integration
   */
  private init(): void {
    // Guard against multiple initializations
    if (window.__scholarSeekbarInitialized) {
      console.log("[ScholarSeekbar] Already initialized, skipping");
      return;
    }
    window.__scholarSeekbarInitialized = true;

    console.log("[ScholarSeekbar] Initializing seekbar integration...");

    // Check if we should use ScitexSeekbar or fall back to noUiSlider
    const useScitexSeekbar = document.querySelector(
      '[data-use-scitex-seekbar="true"]',
    );

    // Skip initialization if sliders are already initialized by noUiSlider
    const yearSlider = document.getElementById(
      "yearSlider",
    ) as NoUiSliderElement | null;
    if (yearSlider?.noUiSlider) {
      console.log(
        "[ScholarSeekbar] noUiSlider already initialized, skipping ScitexSeekbar",
      );
      return;
    }

    if (useScitexSeekbar && typeof ScitexSeekbar !== "undefined") {
      this.initScitexSeekbars();
    } else if (typeof noUiSlider !== "undefined") {
      console.log(
        "[ScholarSeekbar] noUiSlider detected, keeping existing implementation",
      );
    } else {
      console.warn(
        "[ScholarSeekbar] No slider library found. Load either ScitexSeekbar or noUiSlider.",
      );
    }
  }

  /**
   * Initialize SciTeX Seekbars for all filter ranges
   */
  private initScitexSeekbars(): void {
    // Get URL parameters for initial values
    const urlParams = new URLSearchParams(window.location.search);

    // Year Slider
    this.initYearSlider(urlParams);

    // Citations Slider
    this.initCitationsSlider(urlParams);

    // Impact Factor Slider
    this.initImpactFactorSlider(urlParams);

    console.log("[ScholarSeekbar] All seekbars initialized successfully");
  }

  /**
   * Initialize Year Range Slider
   */
  private initYearSlider(urlParams: URLSearchParams): void {
    const container = document.getElementById(
      "yearSlider",
    ) as HTMLElement | null;
    if (!container) return;

    const yearMin = parseInt(urlParams.get("year_from") || "1900") || 1900;
    const yearMax = parseInt(urlParams.get("year_to") || "2025") || 2025;

    // Replace existing container content
    container.innerHTML = "";
    container.classList.add("scitex-seekbar-container");

    // @ts-ignore - ScitexSeekbar library
    this.sliders.year = new ScitexSeekbar(container, {
      min: 1900,
      max: 2025,
      valueMin: yearMin,
      valueMax: yearMax,
      step: 1,
      showValues: false, // Using badge display instead
      format: (value: number) => Math.round(value).toString(),
      onChange: (values: SeekbarValues) => {
        this.updateYearDisplay(values);
        this.updateHiddenInputs("year", values);
      },
      onUpdate: (values: SeekbarValues) => {
        this.updateYearDisplay(values);
      },
    });

    // Initial display update
    this.updateYearDisplay({ min: yearMin, max: yearMax });

    console.log(
      "[ScholarSeekbar] Year slider initialized:",
      yearMin,
      "-",
      yearMax,
    );
  }

  /**
   * Initialize Citations Range Slider
   */
  private initCitationsSlider(urlParams: URLSearchParams): void {
    const container = document.getElementById(
      "citationsSlider",
    ) as HTMLElement | null;
    if (!container) return;

    const citationsMaxRange =
      parseInt(container.dataset.max || "12000") || 12000;
    const citationsMin = parseInt(urlParams.get("min_citations") || "0") || 0;
    const citationsMax =
      parseInt(urlParams.get("max_citations") || "") || citationsMaxRange;

    // Replace existing container content
    container.innerHTML = "";
    container.classList.add("scitex-seekbar-container");

    // @ts-ignore - ScitexSeekbar library
    this.sliders.citations = new ScitexSeekbar(container, {
      min: 0,
      max: citationsMaxRange,
      valueMin: citationsMin,
      valueMax: citationsMax,
      step: Math.max(1, Math.floor(citationsMaxRange / 100)),
      showValues: false,
      format: (value: number) => {
        const v = Math.round(value);
        if (v >= 10000) return (v / 1000).toFixed(0) + "k";
        if (v >= 1000) return (v / 1000).toFixed(1) + "k";
        return v.toString();
      },
      onChange: (values: SeekbarValues) => {
        this.updateCitationsDisplay(values);
        this.updateHiddenInputs("citations", values);
      },
      onUpdate: (values: SeekbarValues) => {
        this.updateCitationsDisplay(values);
      },
    });

    // Initial display update
    this.updateCitationsDisplay({ min: citationsMin, max: citationsMax });

    console.log(
      "[ScholarSeekbar] Citations slider initialized:",
      citationsMin,
      "-",
      citationsMax,
    );
  }

  /**
   * Initialize Impact Factor Range Slider
   */
  private initImpactFactorSlider(urlParams: URLSearchParams): void {
    const container = document.getElementById(
      "impactFactorSlider",
    ) as HTMLElement | null;
    if (!container) return;

    const impactMaxRange = parseFloat(container.dataset.max || "50.0") || 50.0;
    const impactMin =
      parseFloat(urlParams.get("min_impact_factor") || "0") || 0;
    const impactMax =
      parseFloat(urlParams.get("max_impact_factor") || "") || impactMaxRange;

    // Replace existing container content
    container.innerHTML = "";
    container.classList.add("scitex-seekbar-container");

    // @ts-ignore - ScitexSeekbar library
    this.sliders.impactFactor = new ScitexSeekbar(container, {
      min: 0,
      max: impactMaxRange,
      valueMin: impactMin,
      valueMax: impactMax,
      step: Math.max(0.1, impactMaxRange / 100),
      showValues: false,
      format: (value: number) => value.toFixed(1),
      onChange: (values: SeekbarValues) => {
        this.updateImpactFactorDisplay(values);
        this.updateHiddenInputs("impactFactor", values);
      },
      onUpdate: (values: SeekbarValues) => {
        this.updateImpactFactorDisplay(values);
      },
    });

    // Initial display update
    this.updateImpactFactorDisplay({ min: impactMin, max: impactMax });

    console.log(
      "[ScholarSeekbar] Impact Factor slider initialized:",
      impactMin,
      "-",
      impactMax,
    );
  }

  /**
   * Update year display badges
   */
  private updateYearDisplay(values: SeekbarValues): void {
    const minDisplay = document.getElementById(
      "yearMinDisplay",
    ) as HTMLElement | null;
    const maxDisplay = document.getElementById(
      "yearMaxDisplay",
    ) as HTMLElement | null;

    if (minDisplay) minDisplay.textContent = Math.round(values.min).toString();
    if (maxDisplay) maxDisplay.textContent = Math.round(values.max).toString();
  }

  /**
   * Update citations display badges
   */
  private updateCitationsDisplay(values: SeekbarValues): void {
    const minDisplay = document.getElementById(
      "citationsMinDisplay",
    ) as HTMLElement | null;
    const maxDisplay = document.getElementById(
      "citationsMaxDisplay",
    ) as HTMLElement | null;

    if (minDisplay) minDisplay.textContent = Math.round(values.min).toString();
    if (maxDisplay) maxDisplay.textContent = Math.round(values.max).toString();
  }

  /**
   * Update impact factor display badges
   */
  private updateImpactFactorDisplay(values: SeekbarValues): void {
    const minDisplay = document.getElementById(
      "impactFactorMinDisplay",
    ) as HTMLElement | null;
    const maxDisplay = document.getElementById(
      "impactFactorMaxDisplay",
    ) as HTMLElement | null;

    if (minDisplay) minDisplay.textContent = values.min.toFixed(1);
    if (maxDisplay) maxDisplay.textContent = values.max.toFixed(1);
  }

  /**
   * Update hidden form inputs
   */
  private updateHiddenInputs(type: string, values: SeekbarValues): void {
    switch (type) {
      case "year":
        const yearFromInput = document.getElementById(
          "yearFromInput",
        ) as HTMLInputElement | null;
        const yearToInput = document.getElementById(
          "yearToInput",
        ) as HTMLInputElement | null;
        if (yearFromInput)
          yearFromInput.value = Math.round(values.min).toString();
        if (yearToInput) yearToInput.value = Math.round(values.max).toString();
        break;

      case "citations":
        const citationsMinInput = document.getElementById(
          "citationsMinInput",
        ) as HTMLInputElement | null;
        const citationsMaxInput = document.getElementById(
          "citationsMaxInput",
        ) as HTMLInputElement | null;
        if (citationsMinInput)
          citationsMinInput.value = Math.round(values.min).toString();
        if (citationsMaxInput)
          citationsMaxInput.value = Math.round(values.max).toString();
        break;

      case "impactFactor":
        const impactMinInput = document.getElementById(
          "impactFactorMinInput",
        ) as HTMLInputElement | null;
        const impactMaxInput = document.getElementById(
          "impactFactorMaxInput",
        ) as HTMLInputElement | null;
        if (impactMinInput) impactMinInput.value = values.min.toFixed(1);
        if (impactMaxInput) impactMaxInput.value = values.max.toFixed(1);
        break;
    }
  }

  /**
   * Get current slider values
   */
  public getValues(sliderName: string): SeekbarValues | null {
    if (this.sliders[sliderName]) {
      return this.sliders[sliderName].getValues();
    }
    return null;
  }

  /**
   * Set slider values programmatically
   */
  public setValues(sliderName: string, min: number, max: number): void {
    if (this.sliders[sliderName]) {
      this.sliders[sliderName].setValues(min, max);
    }
  }

  /**
   * Reset all sliders to default
   */
  public resetAll(): void {
    Object.keys(this.sliders).forEach((key) => {
      if (this.sliders[key]) {
        this.sliders[key].reset();
      }
    });
  }
}

// Initialize on DOM ready
function initSeekbarIntegration(): void {
  // Only initialize if ScitexSeekbar is available and requested
  if (typeof ScitexSeekbar !== "undefined") {
    window.scholarSeekbar = new ScholarSeekbarIntegration();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initSeekbarIntegration();
  });
} else {
  initSeekbarIntegration();
}
