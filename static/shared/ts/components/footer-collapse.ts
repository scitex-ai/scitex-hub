/**
 * Footer Collapse Toggle + Boundary Drag for Header & Footer
 *
 * Footer: collapsed to a 6px strip on workspace pages.
 * Header & Footer share drag-to-collapse/expand on their boundary edges.
 *
 * Interactions (both header and footer):
 * - Hover near boundary → toggle button appears
 * - Click toggle button → collapse/expand
 * - Single click on collapsed strip → expand
 * - Double-click on expanded area → collapse
 * - Drag from boundary edge → collapse or expand (30px threshold)
 */

const FOOTER_COLLAPSE_KEY = "scitex-footer-collapsed";
const DRAG_THRESHOLD = 30;

/** Position toggle button ON the footer's top edge */
function positionToggle(footer: HTMLElement, toggleBtn: HTMLElement): void {
  const footerHeight = footer.getBoundingClientRect().height;
  toggleBtn.style.bottom = `${footerHeight}px`;
}

function toggleFooter(footer: HTMLElement, toggleBtn: HTMLElement): void {
  const willCollapse = !footer.classList.contains("collapsed");
  footer.classList.toggle("collapsed");
  document.body.classList.toggle("footer-collapsed");

  const tooltip = willCollapse ? "Show footer" : "Hide footer";
  toggleBtn.setAttribute("data-tooltip", tooltip);
  toggleBtn.setAttribute("aria-label", tooltip);

  localStorage.setItem(FOOTER_COLLAPSE_KEY, willCollapse.toString());
  requestAnimationFrame(() => positionToggle(footer, toggleBtn));

  window.dispatchEvent(
    new CustomEvent("footer-collapse-changed", {
      detail: { collapsed: willCollapse },
    }),
  );
}

/** Setup drag-to-collapse/expand on a horizontal boundary */
function setupBoundaryDrag(
  element: HTMLElement,
  edge: "top" | "bottom",
  onToggle: () => void,
): void {
  let dragStartY = 0;
  let isDragging = false;

  element.addEventListener("mousedown", (e: MouseEvent) => {
    const rect = element.getBoundingClientRect();
    const distFromEdge =
      edge === "bottom" ? rect.bottom - e.clientY : e.clientY - rect.top;
    // Start drag only near the boundary edge (within 12px) or when collapsed
    if (distFromEdge < 12 || element.classList.contains("collapsed")) {
      dragStartY = e.clientY;
      isDragging = true;
      document.body.style.cursor = "row-resize";
      e.preventDefault();
    }
  });

  document.addEventListener("mousemove", (e: MouseEvent) => {
    if (!isDragging) return;
    const delta = e.clientY - dragStartY;
    const isCollapsed = element.classList.contains("collapsed");

    let shouldToggle = false;
    if (edge === "bottom") {
      // Header: drag up to collapse, drag down to expand
      shouldToggle =
        (!isCollapsed && delta < -DRAG_THRESHOLD) ||
        (isCollapsed && delta > DRAG_THRESHOLD);
    } else {
      // Footer: drag down to collapse, drag up to expand
      shouldToggle =
        (!isCollapsed && delta > DRAG_THRESHOLD) ||
        (isCollapsed && delta < -DRAG_THRESHOLD);
    }

    if (shouldToggle) {
      // Reset anchor so user can keep dragging back and forth
      dragStartY = e.clientY;
      onToggle();
    }
  });

  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      document.body.style.cursor = "";
    }
  });
}

function initializeFooterCollapse(): void {
  const footer = document.getElementById("site-footer");
  const toggleBtn = document.getElementById("footer-collapse-toggle");

  if (!footer || !toggleBtn) return;

  // Restore saved state (default: collapsed on workspace pages, expanded on landing)
  // Landing page always shows footer expanded regardless of user preference
  const isLanding = document.body.classList.contains("landing-page");
  const saved = localStorage.getItem(FOOTER_COLLAPSE_KEY);
  const isWorkspace = document.body.classList.contains("workspace-page");
  const isCollapsed = isLanding
    ? false
    : saved === null
      ? isWorkspace
      : saved === "true";

  if (isCollapsed) {
    footer.classList.add("collapsed");
    document.body.classList.add("footer-collapsed");
  }

  const tooltip = isCollapsed ? "Show footer" : "Hide footer";
  toggleBtn.setAttribute("data-tooltip", tooltip);
  toggleBtn.setAttribute("aria-label", tooltip);

  positionToggle(footer, toggleBtn);
  window.addEventListener("resize", () => positionToggle(footer, toggleBtn));
  footer.addEventListener("transitionend", () =>
    positionToggle(footer, toggleBtn),
  );

  // Click toggle button
  toggleBtn.addEventListener("click", () => toggleFooter(footer, toggleBtn));

  // Single click on collapsed → expand
  footer.addEventListener("click", () => {
    if (footer.classList.contains("collapsed")) toggleFooter(footer, toggleBtn);
  });

  // Double-click on expanded → collapse
  footer.addEventListener("dblclick", (e: MouseEvent) => {
    if (!footer.classList.contains("collapsed")) {
      e.preventDefault();
      toggleFooter(footer, toggleBtn);
    }
  });

  // Drag on footer boundary
  setupBoundaryDrag(footer, "top", () => toggleFooter(footer, toggleBtn));
}

/** Setup drag on header boundary (header collapse is managed by header.ts) */
function initializeHeaderDrag(): void {
  const header = document.querySelector(".global-header") as HTMLElement;
  if (!header) return;

  setupBoundaryDrag(header, "bottom", () => {
    // Dispatch click on the toggle button to reuse header.ts logic
    const toggleBtn = document.getElementById("header-collapse-toggle");
    toggleBtn?.click();
  });
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initializeFooterCollapse();
    initializeHeaderDrag();
  });
} else {
  initializeFooterCollapse();
  initializeHeaderDrag();
}
