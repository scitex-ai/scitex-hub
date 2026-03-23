/**
 * AJAX Page Loader — re-exports from scitex-ui (single source of truth).
 *
 * Wraps AjaxLoader from scitex-ui with SciTeX Cloud-specific defaults:
 * - Targets #customize-content or #main-content
 * - Uses [data-ajax-load] attribute for link detection
 */

import { AjaxLoader } from "scitex-ui/ts/app/ajax-loader";

let _loader: AjaxLoader | null = null;

/** Initialize delegated click handler for [data-ajax-load] links */
export function initAjaxLinks(): void {
  _loader = new AjaxLoader({
    containerSelector: "#main-content",
    linkSelector: "[data-ajax-load]",
    onLoad: (url, container) => {
      // Also try customize-content if it exists
      const customizeContent = document.getElementById("customize-content");
      if (customizeContent && url.startsWith("/customize/")) {
        customizeContent.innerHTML = container.innerHTML;
      }
    },
  });
  _loader.init();
}

/** Fetch a page via AJAX and inject its content */
export async function loadPageContent(url: string): Promise<void> {
  if (!_loader) {
    _loader = new AjaxLoader({
      containerSelector: "#main-content",
      linkSelector: "[data-ajax-load]",
    });
  }

  // For customize pages, target the right container
  const customizeContent = document.getElementById("customize-content");
  if (customizeContent && url.startsWith("/customize/")) {
    const loader = new AjaxLoader({
      containerSelector: "#customize-content",
      linkSelector: "[data-ajax-load]",
    });
    return loader.load(url);
  }

  return _loader.load(url);
}
