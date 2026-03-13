/**
 * Sphinx inline page navigation — handles page tab clicks and internal links.
 *
 * Uses event delegation on the docs content area so it works after AJAX
 * content replacement without needing to rebind.
 */

function initSphinxPageNav(): void {
  const contentArea = document.getElementById("docs-content-area");
  if (!contentArea) return;

  contentArea.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as HTMLElement;

    // Handle .sphinx-page-link tab clicks
    const pageLink = target.closest<HTMLAnchorElement>(".sphinx-page-link");
    if (pageLink) {
      e.preventDefault();
      const pkgSlug = pageLink.dataset.pkgSlug;
      const sphinxPage = pageLink.dataset.sphinxPage;
      if (pkgSlug && sphinxPage) {
        loadSphinxPage(pkgSlug, sphinxPage, contentArea);
      }
      return;
    }

    // Handle internal Sphinx toctree links (.reference.internal)
    const internalLink = target.closest<HTMLAnchorElement>(
      ".sphinx-inline-content a.reference.internal",
    );
    if (internalLink) {
      const href = internalLink.getAttribute("href");
      if (href && href.endsWith(".html") && !href.startsWith("http")) {
        e.preventDefault();
        // Find the current pkg slug from the wrapper
        const wrapper = contentArea.querySelector("[data-pkg-slug]");
        const slug =
          wrapper?.getAttribute("data-pkg-slug") || getCurrentPkgSlug();
        if (slug) {
          loadSphinxPage(slug, href, contentArea);
        }
      }
    }
  });
}

function getCurrentPkgSlug(): string {
  // Extract from the active sidebar item
  const active = document.querySelector<HTMLAnchorElement>(
    ".docs-nav-item.active",
  );
  return active?.dataset.docSlug || "";
}

function loadSphinxPage(
  slug: string,
  sphinxPage: string,
  contentArea: HTMLElement,
): void {
  contentArea.style.opacity = "0.5";

  const url =
    "/apps/docs/content/" + slug + "/?page=" + encodeURIComponent(sphinxPage);

  fetch(url, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("Failed to load: " + response.status);
      return response.text();
    })
    .then((html) => {
      contentArea.innerHTML = html;
      contentArea.style.opacity = "1";
      contentArea.scrollTop = 0;

      // Move <link> tags to <head>
      contentArea
        .querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')
        .forEach((link) => {
          if (
            !document.querySelector(
              'link[href="' + link.getAttribute("href") + '"]',
            )
          ) {
            document.head.appendChild(link.cloneNode(true));
          }
          link.remove();
        });
    })
    .catch((err: Error) => {
      contentArea.innerHTML =
        '<div class="docs-error"><i class="fas fa-exclamation-triangle"></i> ' +
        err.message +
        "</div>";
      contentArea.style.opacity = "1";
    });
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSphinxPageNav);
} else {
  initSphinxPageNav();
}
