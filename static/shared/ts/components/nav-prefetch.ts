/**
 * Nav Prefetch — preload module pages on hover for instant switching.
 *
 * When a user hovers over a module tab or apps nav item, we inject a
 * <link rel="prefetch"> for that URL. The browser fetches it in the
 * background at low priority. When clicked, the page loads from cache.
 */

function initPrefetch(): void {
  // Target both the module tab bar and the apps navigation sidebar
  const selectors = ".ws-apps-nav-item a, .module-tab-btn, a.module-tab-link";

  document.querySelectorAll<HTMLAnchorElement>(selectors).forEach((link) => {
    if (!link.href || link.href === window.location.href) return;

    link.addEventListener(
      "mouseenter",
      () => {
        // Don't prefetch if already prefetched
        const existing = document.querySelector(
          `link[rel="prefetch"][href="${link.href}"]`,
        );
        if (existing) return;

        const prefetch = document.createElement("link");
        prefetch.rel = "prefetch";
        prefetch.href = link.href;
        document.head.appendChild(prefetch);
      },
      { once: true },
    );
  });
}

// Auto-init
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPrefetch);
} else {
  initPrefetch();
}

export {};
