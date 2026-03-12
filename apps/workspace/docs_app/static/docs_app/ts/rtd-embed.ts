/**
 * Sphinx docs embed viewer for Python Packages docs page.
 * Opens local Sphinx docs in an inline iframe with dark mode support.
 * Falls back to external RTD links for packages without local builds.
 */
(function () {
  const container = document.getElementById(
    "rtd-embed-container",
  ) as HTMLElement | null;
  const iframe = document.getElementById(
    "rtd-embed-iframe",
  ) as HTMLIFrameElement | null;
  const title = document.getElementById(
    "rtd-embed-title",
  ) as HTMLElement | null;
  const extLink = document.getElementById(
    "rtd-embed-external",
  ) as HTMLAnchorElement | null;
  const closeBtn = document.getElementById(
    "rtd-embed-close",
  ) as HTMLElement | null;

  if (!container || !iframe || !title || !extLink || !closeBtn) return;

  const docsContent =
    container.closest(".docs-content") ||
    container.closest("#docs-content-area");

  /** CSS to inject into same-origin Sphinx iframe for dark mode. */
  const DARK_MODE_CSS = `
    body, .wy-body-for-nav, .wy-nav-content-wrap, .wy-nav-content,
    .rst-content, .section, .document {
      background: #1e1e1e !important;
      color: #d4d4d4 !important;
    }
    .wy-side-nav-search, .wy-nav-side {
      background: #151515 !important;
    }
    .wy-side-nav-search input[type="text"] {
      background: #2a2a2a !important;
      color: #d4d4d4 !important;
      border-color: #3a3a3a !important;
    }
    .wy-menu-vertical a, .wy-menu-vertical li a {
      color: #8ba7b8 !important;
    }
    .wy-menu-vertical li.current > a,
    .wy-menu-vertical li.current a:hover {
      background: #2a2a2a !important;
      color: #e6edf3 !important;
    }
    .wy-menu-vertical li.toctree-l1.current > a {
      border-color: #059669 !important;
    }
    a { color: #58a6ff !important; }
    a:hover { color: #79b8ff !important; }
    code, .rst-content code, .rst-content tt {
      background: #2a2a2a !important;
      color: #e06c75 !important;
      border-color: #3a3a3a !important;
    }
    pre, .rst-content pre, .highlight {
      background: #1a1a1a !important;
      border-color: #3a3a3a !important;
    }
    pre code, .highlight code, .highlight pre {
      background: transparent !important;
      color: #d4d4d4 !important;
    }
    h1, h2, h3, h4, h5, h6 {
      color: #e6edf3 !important;
    }
    table, .rst-content table.docutils, .rst-content table.field-list {
      border-color: #3a3a3a !important;
    }
    table th { background: #2a2a2a !important; color: #d4d4d4 !important; }
    table td { background: #1e1e1e !important; color: #d4d4d4 !important; }
    .rst-content .admonition, .rst-content .note {
      background: #2a2a2a !important;
    }
    .rst-content .admonition-title {
      background: #333 !important;
      color: #d4d4d4 !important;
    }
    .wy-breadcrumbs li a, .wy-breadcrumbs-aside a {
      color: #58a6ff !important;
    }
    hr { border-color: #3a3a3a !important; }
    .footer, .rst-footer-buttons {
      background: #151515 !important;
      color: #6c8ba0 !important;
    }
    .btn { background: #2a2a2a !important; color: #d4d4d4 !important;
           border-color: #3a3a3a !important; }
    img { opacity: 0.9; }
  `;

  function isDarkMode(): boolean {
    return (
      document.documentElement.getAttribute("data-theme") === "dark" ||
      !document.documentElement.getAttribute("data-theme")
    );
  }

  function injectDarkMode(iframeEl: HTMLIFrameElement): void {
    if (!isDarkMode()) return;
    try {
      const doc = iframeEl.contentDocument;
      if (!doc) return;
      const existing = doc.getElementById("scitex-dark-mode");
      if (existing) return;
      const style = doc.createElement("style");
      style.id = "scitex-dark-mode";
      style.textContent = DARK_MODE_CSS;
      doc.head.appendChild(style);
    } catch {
      // Cross-origin iframe — cannot inject CSS (external RTD)
    }
  }

  function removeDarkMode(iframeEl: HTMLIFrameElement): void {
    try {
      const doc = iframeEl.contentDocument;
      if (!doc) return;
      const style = doc.getElementById("scitex-dark-mode");
      if (style) style.remove();
    } catch {
      // Cross-origin
    }
  }

  // Inject dark mode CSS on iframe load
  iframe.addEventListener("load", () => {
    if (isDarkMode()) {
      injectDarkMode(iframe);
    }
  });

  // Watch for theme changes
  const observer = new MutationObserver(() => {
    if (isDarkMode()) {
      injectDarkMode(iframe);
    } else {
      removeDarkMode(iframe);
    }
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  // Handle Docs button clicks (local Sphinx docs)
  document
    .querySelectorAll<HTMLAnchorElement>(".pkg-link-docs")
    .forEach((link) => {
      link.addEventListener("click", (e: Event) => {
        e.preventDefault();
        const anchor = e.currentTarget as HTMLAnchorElement;
        const sphinxUrl = anchor.dataset.sphinxUrl || anchor.href;
        const card = anchor.closest(".pkg-card");
        const pkgName = card?.querySelector("strong")?.textContent ?? "";

        title.textContent = `${pkgName} — Documentation`;
        extLink.href = sphinxUrl;
        iframe.src = sphinxUrl;
        container.classList.remove("hidden");
        docsContent?.classList.add("rtd-embed-active");
      });
    });

  closeBtn.addEventListener("click", () => {
    container.classList.add("hidden");
    iframe.src = "";
    docsContent?.classList.remove("rtd-embed-active");
  });
})();
