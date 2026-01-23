/**
 * Product Tour - Step-by-step guided walkthrough for multiple pages
 * Entry point module
 */

import { PageTourConfig } from "./types";
import {
  getPageConfig,
  hasCompletedTour,
  markTourComplete,
  resetTour,
} from "./page-config";
import {
  createOverlay,
  createTooltip,
  positionTooltip,
  highlightElement,
  clearHighlights,
} from "./ui";

console.log("[ProductTour] Module loaded");

// ============================================================================
// Tour State
// ============================================================================

let currentStep = 0;
let currentConfig: PageTourConfig | null = null;
let tourOverlay: HTMLElement | null = null;
let tourTooltip: HTMLElement | null = null;
let isActive = false;

// ============================================================================
// Step Navigation
// ============================================================================

function isElementVisible(el: Element): boolean {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return (
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    style.opacity !== "0" &&
    rect.width > 0 &&
    rect.height > 0
  );
}

function showStep(stepIndex: number): void {
  if (!currentConfig || !tourTooltip) return;
  const steps = currentConfig.steps;

  if (stepIndex < 0 || stepIndex >= steps.length) {
    return;
  }

  const step = steps[stepIndex];
  const element = document.querySelector(step.selector);

  // Check both existence AND visibility
  if (!element || !isElementVisible(element)) {
    console.warn(`[ProductTour] Element not found or hidden: ${step.selector}`);
    // Skip to next step if element not found/hidden
    if (stepIndex < steps.length - 1) {
      showStep(stepIndex + 1);
    } else {
      endTour(true);
    }
    return;
  }

  currentStep = stepIndex;

  // Update tooltip content
  const title = tourTooltip.querySelector(".product-tour-title");
  const description = tourTooltip.querySelector(".product-tour-description");
  const indicator = tourTooltip.querySelector(".product-tour-step-indicator");
  const prevBtn = tourTooltip.querySelector(
    ".product-tour-prev",
  ) as HTMLButtonElement;
  const nextBtn = tourTooltip.querySelector(
    ".product-tour-next",
  ) as HTMLButtonElement;

  if (title) title.textContent = step.title;
  if (description) description.textContent = step.description;
  if (indicator) indicator.textContent = `${stepIndex + 1} / ${steps.length}`;

  // Update button states
  if (prevBtn) {
    prevBtn.style.visibility = stepIndex === 0 ? "hidden" : "visible";
  }
  if (nextBtn) {
    const isLastStep = stepIndex === steps.length - 1;
    nextBtn.innerHTML = "Next &rarr;";
    nextBtn.style.visibility = isLastStep ? "hidden" : "visible";
  }

  // Highlight and position
  highlightElement(element);

  // Position tooltip after a brief delay to ensure layout is stable
  requestAnimationFrame(() => {
    if (tourTooltip) {
      positionTooltip(tourTooltip, element, step);
      tourTooltip.classList.add("visible");
    }
  });
}

function nextStep(): void {
  if (!currentConfig) return;
  // Only advance if not on last step (don't close tour)
  if (currentStep < currentConfig.steps.length - 1) {
    showStep(currentStep + 1);
  }
  // On last step, do nothing - user must use X, Esc, or click outside to close
}

function prevStep(): void {
  if (currentStep > 0) {
    showStep(currentStep - 1);
  }
}

function endTour(completed: boolean = false): void {
  if (!isActive) return;
  isActive = false;

  // Mark complete when tour is finished or closed
  if (currentConfig) {
    markTourComplete(currentConfig.storageKey);
  }

  clearHighlights();

  // Fade out and remove
  tourTooltip?.classList.remove("visible");
  tourOverlay?.classList.remove("visible");

  setTimeout(() => {
    tourOverlay?.remove();
    tourTooltip?.remove();
    tourOverlay = null;
    tourTooltip = null;
    currentConfig = null;
  }, 300);
}

// ============================================================================
// Tour Control
// ============================================================================

function startTour(config?: PageTourConfig): void {
  if (isActive) return;

  // Use provided config or detect from page
  currentConfig = config || getPageConfig();
  if (!currentConfig || currentConfig.steps.length === 0) {
    console.log("[ProductTour] No tour available for this page");
    return;
  }

  isActive = true;
  currentStep = 0;

  // Create elements
  tourOverlay = createOverlay();
  tourTooltip = createTooltip();

  document.body.appendChild(tourOverlay);
  document.body.appendChild(tourTooltip);

  // Setup event listeners
  const closeBtn = tourTooltip.querySelector(".product-tour-close");
  const prevBtn = tourTooltip.querySelector(".product-tour-prev");
  const nextBtn = tourTooltip.querySelector(".product-tour-next");

  closeBtn?.addEventListener("click", () => endTour(false));
  prevBtn?.addEventListener("click", prevStep);
  nextBtn?.addEventListener("click", nextStep);

  // Click on backdrop to skip
  tourOverlay
    .querySelector(".product-tour-backdrop")
    ?.addEventListener("click", () => {
      endTour(false);
    });

  // Keyboard navigation
  const keyHandler = (e: KeyboardEvent) => {
    if (!isActive) {
      document.removeEventListener("keydown", keyHandler);
      return;
    }
    if (e.key === "Escape") {
      endTour(false);
    } else if (e.key === "ArrowRight" || e.key === "Enter") {
      nextStep();
    } else if (e.key === "ArrowLeft") {
      prevStep();
    }
  };
  document.addEventListener("keydown", keyHandler);

  // Show overlay and first step
  requestAnimationFrame(() => {
    tourOverlay?.classList.add("visible");
    showStep(0);
  });
}

// ============================================================================
// Initialization
// ============================================================================

function init(): void {
  console.log("[ProductTour] init() called");
  const config = getPageConfig();
  const isLandingPage = window.location.pathname === "/";

  // Setup tour button for all pages with tour config
  if (config) {
    setupTourButton();
  }

  // Auto-start only on landing page for first-time visitors
  if (isLandingPage && config && !hasCompletedTour(config.storageKey)) {
    console.log("[ProductTour] Scheduling auto-start in 1s");
    setTimeout(() => startTour(config), 1000);
  }

  if (!config) {
    console.log("[ProductTour] No tour configuration for this page");
  }
}

function setupTourButton(): void {
  const tourBtn = document.getElementById("product-tour-btn");
  if (tourBtn) {
    tourBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startTour();
    });
    console.log("[ProductTour] Button handler registered");
  }
}

// ============================================================================
// Exports
// ============================================================================

export function showProductTour(): void {
  startTour();
}

export function resetProductTour(page?: string): void {
  resetTour(page);
}

export function isTourAvailable(): boolean {
  return getPageConfig() !== null;
}

// Expose globally
(window as any).showProductTour = showProductTour;
(window as any).resetProductTour = resetProductTour;
(window as any).isTourAvailable = isTourAvailable;

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
