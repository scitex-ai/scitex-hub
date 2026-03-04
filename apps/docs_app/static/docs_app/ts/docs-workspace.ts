/**
 * Docs workspace — sidebar navigation with two-level hierarchy,
 * AJAX page loading, scrollspy, and export buttons.
 *
 * Reads initial state from data-active-doc attribute on .docs-workspace.
 */

// ── Types & Constants ────────────────────────────────────────

interface SectionInfo {
  id: string;
  title: string;
  element: Element;
  navItem: HTMLElement;
}

const SCROLLSPY_ROOT_MARGIN = "-10% 0px -70% 0px";
const PRINT_CSS =
  "body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#222}" +
  "pre{background:#f5f5f5;padding:1rem;overflow-x:auto;border-radius:4px}" +
  "code{font-family:monospace}h1,h2,h3{margin-top:1.5rem}" +
  "table{border-collapse:collapse;width:100%}" +
  "th,td{border:1px solid #ddd;padding:8px;text-align:left}";

// ── Module State ─────────────────────────────────────────────

let currentSlug = "";
let currentSections: SectionInfo[] = [];
let scrollspyObserver: IntersectionObserver | null = null;

// ── Sidebar Section Nav ──────────────────────────────────────

function clearSectionNav(sidebar: Element): void {
  sidebar.querySelectorAll(".docs-section-item").forEach((el) => el.remove());
  teardownScrollspy();
  currentSections = [];
}

function buildSectionNav(contentArea: HTMLElement, sidebar: Element): void {
  clearSectionNav(sidebar);

  const sections = contentArea.querySelectorAll(".api-section");
  const activePageItem = sidebar.querySelector(".docs-nav-item.active");
  if (!activePageItem || !sections.length) return;

  let insertionPoint: Element = activePageItem;

  sections.forEach((section) => {
    const h2 = section.querySelector("h2");
    if (!h2) return;

    // Find anchor ID from preceding <span id="..."> or section's own id
    let anchorId = "";
    const prev = section.previousElementSibling;
    if (prev && prev.tagName === "SPAN" && prev.id) {
      anchorId = prev.id;
    } else if (section.id) {
      anchorId = section.id;
    }
    if (!anchorId) return;

    // Extract title text (clone to avoid modifying DOM)
    const h2Clone = h2.cloneNode(true) as HTMLElement;
    h2Clone.querySelectorAll(".anchor-link").forEach((el) => el.remove());
    const title = h2Clone.textContent?.trim() ?? "";
    if (!title) return;

    // Create sidebar sub-item
    const navItem = document.createElement("a");
    navItem.className = "docs-section-item";
    navItem.href = "#" + currentSlug + "--" + anchorId;
    navItem.textContent = title;
    navItem.dataset.sectionId = anchorId;

    navItem.addEventListener("click", (e) => {
      e.preventDefault();
      const target = prev?.id === anchorId ? prev : section;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", "#" + currentSlug + "--" + anchorId);
    });

    // Insert after the previous insertion point (maintains document order)
    insertionPoint.after(navItem);
    insertionPoint = navItem;

    currentSections.push({ id: anchorId, title, element: section, navItem });
  });

  setupScrollspy(contentArea);
}

// ── Scrollspy ────────────────────────────────────────────────

function setupScrollspy(contentArea: HTMLElement): void {
  teardownScrollspy();
  if (!currentSections.length) return;

  scrollspyObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const section = currentSections.find((s) => s.element === entry.target);
        if (section) {
          currentSections.forEach((s) => s.navItem.classList.remove("active"));
          section.navItem.classList.add("active");
        }
      });
    },
    {
      root: contentArea,
      rootMargin: SCROLLSPY_ROOT_MARGIN,
      threshold: 0,
    },
  );

  currentSections.forEach((s) => scrollspyObserver!.observe(s.element));
}

function teardownScrollspy(): void {
  if (scrollspyObserver) {
    scrollspyObserver.disconnect();
    scrollspyObserver = null;
  }
}

// ── Export Helpers ────────────────────────────────────────────

function openPrintWindow(html: string): void {
  const win = window.open("", "_blank");
  if (!win) return;
  const doc = win.document;
  doc.open();
  doc.write(
    "<!DOCTYPE html><html><head><title>SciTeX Docs</title></head><body></body></html>",
  );
  doc.close();
  const s = doc.createElement("style");
  s.textContent = PRINT_CSS;
  doc.head.appendChild(s);
  doc.body.innerHTML = html;
  win.print();
}

function injectSectionExportButtons(
  slug: string,
  contentArea: HTMLElement,
): void {
  if (contentArea.querySelector(".docs-section-export")) return;
  const bar = document.createElement("div");
  bar.className = "docs-section-export";
  bar.innerHTML =
    '<div class="docs-dropdown">' +
    '<button class="docs-export-btn docs-dropdown-toggle">' +
    '<i class="fas fa-download"></i> Download</button>' +
    '<div class="docs-dropdown-menu">' +
    '<a href="/docs/export/' +
    slug +
    '/" class="docs-dropdown-item">' +
    '<i class="fas fa-file-alt"></i> .md</a>' +
    '<button class="docs-dropdown-item docs-section-pdf-btn">' +
    '<i class="fas fa-file-pdf"></i> .pdf</button>' +
    "</div></div>";
  const pdfBtn = bar.querySelector<HTMLButtonElement>(".docs-section-pdf-btn");
  if (pdfBtn) {
    pdfBtn.onclick = () => openPrintWindow(contentArea.innerHTML);
  }
  contentArea.insertBefore(bar, contentArea.firstChild);
}

// ── AJAX Page Loading ────────────────────────────────────────

function loadDocPage(
  slug: string,
  anchorId: string | undefined,
  contentArea: HTMLElement,
  sidebar: Element,
  navItems: NodeListOf<HTMLAnchorElement>,
): void {
  if (!slug) return;
  currentSlug = slug;

  // Update URL hash
  const hashValue = anchorId ? slug + "--" + anchorId : slug;
  history.replaceState(null, "", "#" + hashValue);

  // Update active state in sidebar (clear section items first)
  clearSectionNav(sidebar);
  navItems.forEach((item) => {
    item.classList.toggle("active", item.dataset.slug === slug);
  });

  // Show loading
  contentArea.style.opacity = "0.5";

  fetch("/docs/content/" + slug + "/", {
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

      // Execute inline scripts
      contentArea.querySelectorAll("script").forEach((oldScript) => {
        const newScript = document.createElement("script");
        if (oldScript.type) newScript.type = oldScript.type;
        if (oldScript.src) {
          newScript.src = oldScript.src;
        } else {
          newScript.textContent = oldScript.textContent;
        }
        oldScript.parentNode?.replaceChild(newScript, oldScript);
      });

      // Build section nav + scrollspy (replaces foldSections)
      buildSectionNav(contentArea, sidebar);

      // Inject export buttons
      injectSectionExportButtons(slug, contentArea);

      // Scroll to anchor if specified
      if (anchorId) {
        const target = document.getElementById(anchorId);
        if (target) {
          setTimeout(
            () => target.scrollIntoView({ behavior: "smooth", block: "start" }),
            100,
          );
          // Highlight the matching section nav item
          const matchingNav = currentSections.find((s) => s.id === anchorId);
          if (matchingNav) {
            currentSections.forEach((s) =>
              s.navItem.classList.remove("active"),
            );
            matchingNav.navItem.classList.add("active");
          }
        }
      }
    })
    .catch((err: Error) => {
      contentArea.innerHTML =
        '<div class="docs-error"><i class="fas fa-exclamation-triangle"></i> ' +
        err.message +
        "</div>";
      contentArea.style.opacity = "1";
    });
}

// ── Dropdown Toggle ──────────────────────────────────────────

function initDropdowns(): void {
  document.addEventListener("click", (e) => {
    const toggle = (e.target as Element).closest(".docs-dropdown-toggle");
    if (toggle) {
      e.preventDefault();
      e.stopPropagation();
      const dropdown = toggle.closest(".docs-dropdown");
      if (!dropdown) return;
      // Close other dropdowns
      document
        .querySelectorAll(".docs-dropdown.open")
        .forEach((d) => d !== dropdown && d.classList.remove("open"));
      dropdown.classList.toggle("open");
      return;
    }
    // Close all dropdowns on outside click
    document
      .querySelectorAll(".docs-dropdown.open")
      .forEach((d) => d.classList.remove("open"));
  });
}

// ── Initialization ───────────────────────────────────────────

function initDocsWorkspace(): void {
  const workspace = document.querySelector<HTMLElement>(".docs-workspace");
  const sidebar = document.querySelector(".docs-sidebar");
  const contentArea = document.getElementById("docs-content-area");
  if (!workspace || !sidebar || !contentArea) return;

  const navItems =
    sidebar.querySelectorAll<HTMLAnchorElement>(".docs-nav-item");
  currentSlug = workspace.dataset.activeDoc ?? "";

  // Dropdown toggles
  initDropdowns();

  // Global "All PDF" button
  const allPdfBtn = document.getElementById("docs-export-all-pdf");
  if (allPdfBtn) {
    allPdfBtn.onclick = () => {
      const slugs = Array.from(navItems).map((i) => i.dataset.slug ?? "");
      const fetches = slugs.map((s) =>
        fetch("/docs/content/" + s + "/", {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        }).then((r) => r.text()),
      );
      Promise.all(fetches).then((pages) => {
        const combined = pages
          .map((html, i) => "<h1>" + slugs[i] + "</h1>" + html)
          .join('<hr class="docs-print-page-break" />');
        openPrintWindow(combined);
      });
    };
  }

  // Sidebar click handlers
  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      loadDocPage(
        item.dataset.slug ?? "",
        undefined,
        contentArea,
        sidebar,
        navItems,
      );
    });
  });

  // Parse hash: /docs/#slug or /docs/#slug--sectionId
  const hash = window.location.hash.replace("#", "");
  if (hash) {
    const parts = hash.split("--");
    const slugFromHash = parts[0];
    const anchorFromHash = parts[1] || undefined;
    const matchedItem = Array.from(navItems).find(
      (i) => i.dataset.slug === slugFromHash,
    );
    if (matchedItem) {
      currentSlug = slugFromHash;
      loadDocPage(currentSlug, anchorFromHash, contentArea, sidebar, navItems);
    } else {
      loadDocPage(currentSlug, hash, contentArea, sidebar, navItems);
    }
  } else {
    loadDocPage(currentSlug, undefined, contentArea, sidebar, navItems);
  }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDocsWorkspace);
} else {
  initDocsWorkspace();
}
