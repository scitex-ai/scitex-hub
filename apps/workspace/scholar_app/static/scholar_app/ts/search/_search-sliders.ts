/**
 * Search Sliders - noUiSlider initialization and operator application
 */

// noUiSlider is loaded externally via CDN
declare const noUiSlider: any;

import type { SearchPreferences } from "./_search-preferences";
import type { ParsedOperators } from "./_search-operators";

// Initialize sliders
export function initSliders(
  prefs: SearchPreferences | null,
  onChangeCb: () => void,
): void {
  // Year slider
  const yearSlider = document.getElementById("yearSlider") as HTMLElement & {
    noUiSlider?: any;
  };
  if (yearSlider && typeof noUiSlider !== "undefined") {
    const yearMin = parseInt(yearSlider.dataset.min || "1900");
    const yearMax = parseInt(yearSlider.dataset.max || "2025");
    const yearFromVal = prefs?.yearFrom ? parseInt(prefs.yearFrom) : yearMin;
    const yearToVal = prefs?.yearTo ? parseInt(prefs.yearTo) : yearMax;

    noUiSlider.create(yearSlider, {
      start: [yearFromVal, yearToVal],
      connect: true,
      range: { min: yearMin, max: yearMax },
      step: 1,
    });

    yearSlider.noUiSlider?.on("update", (values: (string | number)[]) => {
      const minDisplay = document.getElementById("yearMinDisplay");
      const maxDisplay = document.getElementById("yearMaxDisplay");
      const minInput = document.getElementById(
        "yearFromInput",
      ) as HTMLInputElement;
      const maxInput = document.getElementById(
        "yearToInput",
      ) as HTMLInputElement;

      if (minDisplay)
        minDisplay.textContent = Math.round(Number(values[0])).toString();
      if (maxDisplay)
        maxDisplay.textContent = Math.round(Number(values[1])).toString();
      if (minInput) minInput.value = Math.round(Number(values[0])).toString();
      if (maxInput) maxInput.value = Math.round(Number(values[1])).toString();
    });
    yearSlider.noUiSlider?.on("change", onChangeCb);
  }

  // Citations slider
  const citSlider = document.getElementById(
    "citationsSlider",
  ) as HTMLElement & { noUiSlider?: any };
  if (citSlider && typeof noUiSlider !== "undefined") {
    const citMax = parseInt(citSlider.dataset.max || "12000");
    const citMinVal = prefs?.citationsMin ? parseInt(prefs.citationsMin) : 0;
    const citMaxVal = prefs?.citationsMax
      ? parseInt(prefs.citationsMax)
      : citMax;

    noUiSlider.create(citSlider, {
      start: [citMinVal, citMaxVal],
      connect: true,
      range: { min: 0, max: citMax },
      step: 100,
    });

    citSlider.noUiSlider?.on("update", (values: (string | number)[]) => {
      const minDisplay = document.getElementById("citationsMinDisplay");
      const maxDisplay = document.getElementById("citationsMaxDisplay");
      const minInput = document.getElementById(
        "citationsMinInput",
      ) as HTMLInputElement;
      const maxInput = document.getElementById(
        "citationsMaxInput",
      ) as HTMLInputElement;

      if (minDisplay)
        minDisplay.textContent = Math.round(Number(values[0])).toString();
      if (maxDisplay)
        maxDisplay.textContent = Math.round(Number(values[1])).toString();
      if (minInput) minInput.value = Math.round(Number(values[0])).toString();
      if (maxInput) maxInput.value = Math.round(Number(values[1])).toString();
    });
    citSlider.noUiSlider?.on("change", onChangeCb);
  }

  // Impact Factor slider
  const ifSlider = document.getElementById(
    "impactFactorSlider",
  ) as HTMLElement & { noUiSlider?: any };
  if (ifSlider && typeof noUiSlider !== "undefined") {
    const ifMax = parseFloat(ifSlider.dataset.max || "50.0");
    const ifMinVal = prefs?.impactFactorMin
      ? parseFloat(prefs.impactFactorMin)
      : 0;
    const ifMaxVal = prefs?.impactFactorMax
      ? parseFloat(prefs.impactFactorMax)
      : ifMax;

    noUiSlider.create(ifSlider, {
      start: [ifMinVal, ifMaxVal],
      connect: true,
      range: { min: 0, max: ifMax },
      step: 0.5,
    });

    ifSlider.noUiSlider?.on("update", (values: (string | number)[]) => {
      const minDisplay = document.getElementById("impactFactorMinDisplay");
      const maxDisplay = document.getElementById("impactFactorMaxDisplay");
      const minInput = document.getElementById(
        "impactFactorMinInput",
      ) as HTMLInputElement;
      const maxInput = document.getElementById(
        "impactFactorMaxInput",
      ) as HTMLInputElement;

      if (minDisplay)
        minDisplay.textContent = parseFloat(String(values[0])).toFixed(1);
      if (maxDisplay)
        maxDisplay.textContent = parseFloat(String(values[1])).toFixed(1);
      if (minInput) minInput.value = parseFloat(String(values[0])).toFixed(1);
      if (maxInput) maxInput.value = parseFloat(String(values[1])).toFixed(1);
    });
    ifSlider.noUiSlider?.on("change", onChangeCb);
  }
}

// Apply parsed operators to form fields before search
export function applyOperatorsToForm(operators: ParsedOperators): void {
  // Author field (join multiple includes with comma)
  if (operators.authorIncludes.length > 0) {
    const authorInput = document.querySelector<HTMLInputElement>(
      'input[name="author"]',
    );
    if (authorInput) authorInput.value = operators.authorIncludes.join(", ");
  }

  // Journal field (join multiple includes with comma)
  if (operators.journalIncludes.length > 0) {
    const journalInput = document.querySelector<HTMLInputElement>(
      'input[name="journal"]',
    );
    if (journalInput) journalInput.value = operators.journalIncludes.join(", ");
  }

  // Year range sliders
  const yearSlider = document.getElementById("yearSlider") as HTMLElement & {
    noUiSlider?: any;
  };
  if (yearSlider?.noUiSlider) {
    const currentMin = parseInt(
      (document.getElementById("yearFromInput") as HTMLInputElement)?.value ||
        "1900",
    );
    const currentMax = parseInt(
      (document.getElementById("yearToInput") as HTMLInputElement)?.value ||
        "2025",
    );
    const yearFrom = operators.yearFrom ?? currentMin;
    const yearTo = operators.yearTo ?? currentMax;
    yearSlider.noUiSlider.set([yearFrom, yearTo]);
  }

  // Citations slider (set low/high)
  const citSlider = document.getElementById(
    "citationsSlider",
  ) as HTMLElement & { noUiSlider?: any };
  if (citSlider?.noUiSlider) {
    const currentMin = parseInt(
      (document.getElementById("citationsMinInput") as HTMLInputElement)
        ?.value || "0",
    );
    const currentMax = parseInt(
      (document.getElementById("citationsMaxInput") as HTMLInputElement)
        ?.value || "128",
    );
    const citLow = operators.citationsLow ?? currentMin;
    const citHigh = operators.citationsHigh ?? currentMax;
    citSlider.noUiSlider.set([citLow, citHigh]);
  }

  // Impact factor slider (set low/high)
  const ifSlider = document.getElementById(
    "impactFactorSlider",
  ) as HTMLElement & { noUiSlider?: any };
  if (ifSlider?.noUiSlider) {
    const currentMin = parseFloat(
      (document.getElementById("impactFactorMinInput") as HTMLInputElement)
        ?.value || "0",
    );
    const currentMax = parseFloat(
      (document.getElementById("impactFactorMaxInput") as HTMLInputElement)
        ?.value || "50",
    );
    const ifLow = operators.impactFactorLow ?? currentMin;
    const ifHigh = operators.impactFactorHigh ?? currentMax;
    ifSlider.noUiSlider.set([ifLow, ifHigh]);
  }
}
