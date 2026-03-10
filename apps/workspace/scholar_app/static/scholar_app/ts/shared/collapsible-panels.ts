/**

 * Collapsible Panels Module
 *
 * Generic module for handling collapsible panel UI interactions:
 * - Click to expand/collapse panels
 * - Icon rotation animation
 * - Dynamic height calculation with MutationObserver
 * - Smooth transitions
 *
 * @module shared/collapsible-panels
 */

interface CollapsiblePanelElements {
  header: HTMLElement;
  content: HTMLElement;
  icon: HTMLElement;
}

/**
 * Recalculate height of collapsible content
 * Useful when content changes dynamically
 *
 * @param {HTMLElement} content - The collapsible content element
 */
function recalculateHeight(content: HTMLElement): void {
  if (
    content.style.display !== "none" &&
    content.classList.contains("expanded")
  ) {
    console.log("[Collapsible Panels] Recalculating height for:", content);
    content.style.maxHeight = content.scrollHeight + "px";
  }
}

/**
 * Expand a collapsible panel
 *
 * @param {HTMLElement} header - The header element
 * @param {HTMLElement} content - The content element to expand
 * @param {HTMLElement} icon - The icon element to rotate
 */
function expandPanel(
  header: HTMLElement,
  content: HTMLElement,
  icon: HTMLElement,
): void {
  console.log("[Collapsible Panels] Expanding panel");

  header.classList.add("expanded");
  content.classList.add("expanded");
  content.style.display = "block";
  content.style.maxHeight = content.scrollHeight + "px";
  icon.style.transform = "rotate(180deg)";

  // Set up MutationObserver to recalculate height on content changes
  const observer = new MutationObserver(() => recalculateHeight(content));
  observer.observe(content, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  // Store observer on element for cleanup
  (content as any).__heightObserver = observer;
}

/**
 * Collapse a collapsible panel
 *
 * @param {HTMLElement} header - The header element
 * @param {HTMLElement} content - The content element to collapse
 * @param {HTMLElement} icon - The icon element to rotate
 */
function collapsePanel(
  header: HTMLElement,
  content: HTMLElement,
  icon: HTMLElement,
): void {
  console.log("[Collapsible Panels] Collapsing panel");

  header.classList.remove("expanded");
  content.classList.remove("expanded");
  content.style.maxHeight = "0px";
  content.style.display = "none";
  icon.style.transform = "rotate(0deg)";

  // Disconnect observer if exists
  const observer = (content as any).__heightObserver;
  if (observer) {
    observer.disconnect();
    delete (content as any).__heightObserver;
  }
}

/**
 * Toggle a collapsible panel between expanded and collapsed states
 *
 * @param {HTMLElement} header - The header element
 * @param {HTMLElement} content - The content element
 * @param {HTMLElement} icon - The icon element
 */
function togglePanel(
  header: HTMLElement,
  content: HTMLElement,
  icon: HTMLElement,
): void {
  const isExpanded = header.classList.contains("expanded");

  if (isExpanded) {
    collapsePanel(header, content, icon);
  } else {
    expandPanel(header, content, icon);
  }
}

/**
 * Initialize a single collapsible panel
 *
 * @param {HTMLElement} header - The collapsible header element
 */
function initializePanel(header: HTMLElement): void {
  const content = header.nextElementSibling as HTMLElement;
  const icon = header.querySelector(".collapse-icon") as HTMLElement;

  if (!content || !icon) {
    console.warn(
      "[Collapsible Panels] Missing content or icon for header:",
      header,
    );
    return;
  }

  console.log("[Collapsible Panels] Initializing panel:", header);

  header.addEventListener("click", (e: Event) => {
    e.preventDefault();
    togglePanel(header, content, icon);
  });
}

/**
 * Initialize all collapsible panels on the page
 * Should be called after DOM is loaded
 *
 * @param {string} headerSelector - CSS selector for collapsible headers (default: '.collapsible-header')
 */
function initializeCollapsiblePanels(
  headerSelector: string = ".collapsible-header",
): void {
  console.log(
    "[Collapsible Panels] Initializing all panels with selector:",
    headerSelector,
  );

  const headers = document.querySelectorAll(headerSelector);

  if (headers.length === 0) {
    console.log("[Collapsible Panels] No collapsible panels found");
    return;
  }

  console.log("[Collapsible Panels] Found", headers.length, "panels");

  headers.forEach((header) => {
    initializePanel(header as HTMLElement);
  });

  console.log("[Collapsible Panels] Initialization complete");
}

/**
 * Expand all collapsible panels
 *
 * @param {string} headerSelector - CSS selector for collapsible headers (default: '.collapsible-header')
 */
function expandAllPanels(headerSelector: string = ".collapsible-header"): void {
  console.log("[Collapsible Panels] Expanding all panels");

  const headers = document.querySelectorAll(headerSelector);

  headers.forEach((header) => {
    const content = header.nextElementSibling as HTMLElement;
    const icon = header.querySelector(".collapse-icon") as HTMLElement;

    if (content && icon && !header.classList.contains("expanded")) {
      expandPanel(header as HTMLElement, content, icon);
    }
  });
}

/**
 * Collapse all collapsible panels
 *
 * @param {string} headerSelector - CSS selector for collapsible headers (default: '.collapsible-header')
 */
function collapseAllPanels(
  headerSelector: string = ".collapsible-header",
): void {
  console.log("[Collapsible Panels] Collapsing all panels");

  const headers = document.querySelectorAll(headerSelector);

  headers.forEach((header) => {
    const content = header.nextElementSibling as HTMLElement;
    const icon = header.querySelector(".collapse-icon") as HTMLElement;

    if (content && icon && header.classList.contains("expanded")) {
      collapsePanel(header as HTMLElement, content, icon);
    }
  });
}

// Auto-initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () =>
    initializeCollapsiblePanels(),
  );
} else {
  initializeCollapsiblePanels();
}

// Export functions for external use
export {
  initializeCollapsiblePanels,
  initializePanel,
  togglePanel,
  expandPanel,
  collapsePanel,
  expandAllPanels,
  collapseAllPanels,
  recalculateHeight,
};
