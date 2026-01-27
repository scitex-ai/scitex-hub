/**
 * Product Tour UI Components
 */
import { TourStep } from "./types";

export function createOverlay(): HTMLElement {
  const overlay = document.createElement("div");
  overlay.className = "product-tour-overlay";
  overlay.innerHTML = `<div class="product-tour-backdrop"></div>`;
  return overlay;
}

export function createTooltip(): HTMLElement {
  const tooltip = document.createElement("div");
  tooltip.className = "product-tour-tooltip";
  tooltip.innerHTML = `
    <div class="product-tour-tooltip-content">
      <div class="product-tour-tooltip-header">
        <span class="product-tour-step-indicator"></span>
        <button class="product-tour-close" title="Close (Esc)"><i class="fas fa-times"></i></button>
      </div>
      <h3 class="product-tour-title"></h3>
      <p class="product-tour-description"></p>
      <div class="product-tour-actions">
        <button class="product-tour-btn product-tour-prev">&larr; Previous</button>
        <button class="product-tour-btn product-tour-next primary">Next &rarr;</button>
      </div>
    </div>
    <div class="product-tour-arrow"></div>
  `;
  return tooltip;
}

export function positionTooltip(
  tooltip: HTMLElement,
  element: Element,
  step: TourStep,
): void {
  const rect = element.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  const position = step.position || "bottom";
  const arrow = tooltip.querySelector(".product-tour-arrow") as HTMLElement;

  let top = 0;
  let left = 0;
  const gap = 12;

  // Reset arrow classes
  arrow.className = "product-tour-arrow";

  switch (position) {
    case "bottom":
      top = rect.bottom + gap;
      left = rect.left + rect.width / 2 - tooltipRect.width / 2;
      arrow.classList.add("arrow-top");
      break;
    case "top":
      top = rect.top - tooltipRect.height - gap;
      left = rect.left + rect.width / 2 - tooltipRect.width / 2;
      arrow.classList.add("arrow-bottom");
      break;
    case "left":
      top = rect.top + rect.height / 2 - tooltipRect.height / 2;
      left = rect.left - tooltipRect.width - gap;
      arrow.classList.add("arrow-right");
      break;
    case "right":
      top = rect.top + rect.height / 2 - tooltipRect.height / 2;
      left = rect.right + gap;
      arrow.classList.add("arrow-left");
      break;
  }

  // Keep tooltip within viewport
  const padding = 16;
  left = Math.max(
    padding,
    Math.min(left, window.innerWidth - tooltipRect.width - padding),
  );
  top = Math.max(
    padding,
    Math.min(top, window.innerHeight - tooltipRect.height - padding),
  );

  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${left}px`;

  // Position arrow to point at element center
  const arrowLeft = rect.left + rect.width / 2 - left;
  arrow.style.left = `${Math.max(20, Math.min(arrowLeft, tooltipRect.width - 20))}px`;
}

// Store reference to highlight overlay
let highlightOverlay: HTMLElement | null = null;

export function highlightElement(element: Element): void {
  // Remove previous highlight overlay
  clearHighlights();

  // Create highlight overlay element
  highlightOverlay = document.createElement("div");
  highlightOverlay.className = "product-tour-highlight-overlay";
  document.body.appendChild(highlightOverlay);

  // Get element position relative to viewport
  const rect = element.getBoundingClientRect();

  // Calculate visible portion (intersection with viewport)
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  const visibleTop = Math.max(0, rect.top);
  const visibleLeft = Math.max(0, rect.left);
  const visibleRight = Math.min(viewportWidth, rect.right);
  const visibleBottom = Math.min(viewportHeight, rect.bottom);

  const visibleWidth = Math.max(0, visibleRight - visibleLeft);
  const visibleHeight = Math.max(0, visibleBottom - visibleTop);

  // Position overlay only on visible portion
  highlightOverlay.style.position = "fixed";
  highlightOverlay.style.boxSizing = "border-box";
  highlightOverlay.style.top = `${visibleTop}px`;
  highlightOverlay.style.left = `${visibleLeft}px`;
  highlightOverlay.style.width = `${visibleWidth}px`;
  highlightOverlay.style.height = `${visibleHeight}px`;
  highlightOverlay.style.pointerEvents = "none";
  highlightOverlay.style.zIndex = "10001";
  highlightOverlay.style.border = "4px solid var(--accent-color, #6366f1)";
  highlightOverlay.style.borderRadius = "8px";
  highlightOverlay.style.boxShadow =
    "inset 0 0 20px rgba(99, 102, 241, 0.3), 0 0 20px rgba(99, 102, 241, 0.4)";
  highlightOverlay.style.animation =
    "product-tour-pulse 2s ease-in-out infinite";
}

export function clearHighlights(): void {
  // Remove overlay element
  if (highlightOverlay) {
    highlightOverlay.remove();
    highlightOverlay = null;
  }
  // Also remove any class-based highlights (legacy)
  document.querySelectorAll(".product-tour-highlight").forEach((el) => {
    el.classList.remove("product-tour-highlight");
  });
}

// Restart hint tooltip (shown under tour button during tour)
let restartHintTooltip: HTMLElement | null = null;
let tourBtnHighlight: HTMLElement | null = null;

export function showRestartHint(): void {
  const tourBtn = document.getElementById("product-tour-btn");
  if (!tourBtn || restartHintTooltip) return;

  // Create tooltip with same style as main tour tooltip
  restartHintTooltip = document.createElement("div");
  restartHintTooltip.className =
    "product-tour-tooltip product-tour-restart-tooltip";
  restartHintTooltip.innerHTML = `
    <div class="product-tour-tooltip-content">
      <div class="product-tour-tooltip-header">
        <span class="product-tour-step-indicator" style="color: var(--accent-color, #6366f1);">
          <i class="fas fa-redo"></i> Tip
        </span>
      </div>
      <h3 class="product-tour-title">Restart Tour Anytime</h3>
      <p class="product-tour-description">Click this button to restart the tour whenever you need a refresher.</p>
    </div>
    <div class="product-tour-arrow arrow-top"></div>
  `;
  document.body.appendChild(restartHintTooltip);

  // Create highlight overlay for tour button (same style as main tour highlights)
  tourBtnHighlight = document.createElement("div");
  tourBtnHighlight.className = "product-tour-highlight-overlay";
  document.body.appendChild(tourBtnHighlight);

  const rect = tourBtn.getBoundingClientRect();
  tourBtnHighlight.style.position = "fixed";
  tourBtnHighlight.style.boxSizing = "border-box";
  tourBtnHighlight.style.top = `${rect.top}px`;
  tourBtnHighlight.style.left = `${rect.left}px`;
  tourBtnHighlight.style.width = `${rect.width}px`;
  tourBtnHighlight.style.height = `${rect.height}px`;
  tourBtnHighlight.style.pointerEvents = "none";
  tourBtnHighlight.style.zIndex = "10001";
  tourBtnHighlight.style.border = "4px solid var(--accent-color, #6366f1)";
  tourBtnHighlight.style.borderRadius = "8px";
  tourBtnHighlight.style.boxShadow =
    "inset 0 0 20px rgba(99, 102, 241, 0.3), 0 0 20px rgba(99, 102, 241, 0.4)";
  tourBtnHighlight.style.animation =
    "product-tour-pulse 2s ease-in-out infinite";

  // Position below the tour button
  requestAnimationFrame(() => {
    if (!restartHintTooltip || !tourBtn) return;
    const rect = tourBtn.getBoundingClientRect();
    const tooltipRect = restartHintTooltip.getBoundingClientRect();
    const gap = 12;

    let top = rect.bottom + gap;
    let left = rect.left + rect.width / 2 - tooltipRect.width / 2;

    // Keep within viewport
    const padding = 16;
    left = Math.max(
      padding,
      Math.min(left, window.innerWidth - tooltipRect.width - padding),
    );

    restartHintTooltip.style.top = `${top}px`;
    restartHintTooltip.style.left = `${left}px`;

    // Position arrow
    const arrow = restartHintTooltip.querySelector(
      ".product-tour-arrow",
    ) as HTMLElement;
    if (arrow) {
      const arrowLeft = rect.left + rect.width / 2 - left;
      arrow.style.left = `${Math.max(20, Math.min(arrowLeft, tooltipRect.width - 20))}px`;
    }

    restartHintTooltip.classList.add("visible");
  });
}

export function hideRestartHint(): void {
  if (restartHintTooltip) {
    restartHintTooltip.classList.remove("visible");
    setTimeout(() => {
      restartHintTooltip?.remove();
      restartHintTooltip = null;
    }, 300);
  }
  // Remove highlight overlay from tour button
  if (tourBtnHighlight) {
    tourBtnHighlight.remove();
    tourBtnHighlight = null;
  }
}
