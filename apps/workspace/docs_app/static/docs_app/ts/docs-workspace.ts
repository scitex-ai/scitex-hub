/**
 * Docs workspace — sidebar navigation with two-level hierarchy,
 * AJAX page loading, scrollspy, and export buttons.
 *
 * Reads initial state from data-active-doc attribute on .docs-workspace.
 */

import { openPrintWindow } from "./docs-print";
import { printAllDocs } from "./docs-batch-print";
import { PRINT_CSS } from "./docs-export-style";
import { initDocsHtmlExport } from "./docs-html-export";
import { initDocsColumns, syncDocsColumns } from "./docs-navigation";
import { initDocsFilter } from "./docs-filter";
import { initDocsCopy } from "./docs-copy";
import { initMobileCascade, syncMobileCascade } from "./docs-mobile-nav";

// ── Types & Constants ────────────────────────────────────────

interface SectionInfo {
  id: string;
  title: string;
  element: Element;
  navItem: HTMLElement;
}

const SCROLLSPY_ROOT_MARGIN = "-10% 0px -70% 0px";

// ── Module State ─────────────────────────────────────────────

let currentSlug = "";
let loadRequest = 0;
let currentSections: SectionInfo[] = [];
let scrollspyObserver: IntersectionObserver | null = null;
const selectedSlugs = new Set<string>();

// ── Sidebar Section Nav ──────────────────────────────────────

function clearSectionNav(sidebar: Element): void {
  sidebar.querySelectorAll(".docs-section-item").forEach((el) => el.remove());
  const sectionNav = sidebar.querySelector<HTMLElement>(".docs-section-nav");
  if (sectionNav) sectionNav.hidden = true;
  teardownScrollspy();
  currentSections = [];
}

function buildSectionNav(contentArea: HTMLElement, sidebar: Element): void {
  clearSectionNav(sidebar);

  const sections = contentArea.querySelectorAll(".api-section");
  const activePageItem = sidebar.querySelector(".docs-nav-item.active");
  if (!activePageItem || !sections.length) return;

  const sectionNav = sidebar.querySelector<HTMLElement>(".docs-section-nav");
  if (!sectionNav) return;

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

    sectionNav.appendChild(navItem);
    sectionNav.hidden = false;

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

// ── AJAX Page Loading ────────────────────────────────────────

function loadDocPage(
  slug: string,
  anchorId: string | undefined,
  contentArea: HTMLElement,
  sidebar: Element,
  navItems: NodeListOf<HTMLAnchorElement>,
  sphinxPage?: string,
): void {
  if (!slug) return;
  currentSlug = slug;
  const request = ++loadRequest;
  syncDocsColumns(slug);

  // Update URL hash
  const hashValue = anchorId ? slug + "--" + anchorId : slug;
  history.replaceState(null, "", "#" + hashValue);

  // Update active state in sidebar (clear section items first)
  clearSectionNav(sidebar);
  navItems.forEach((item) => {
    const active = item.dataset.docSlug === slug;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });

  // Keep the mobile cascade dropdowns (section → page) in sync
  syncMobileCascade(slug);

  // Show loading
  contentArea.style.opacity = "0.5";

  let url = "/apps/docs/content/" + encodeURIComponent(slug) + "/";
  if (sphinxPage) url += "?page=" + encodeURIComponent(sphinxPage);

  fetch(url, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("Failed to load: " + response.status);
      return response.text();
    })
    .then((html) => {
      if (request !== loadRequest || !contentArea.isConnected) return;
      contentArea.innerHTML = html;
      contentArea.style.opacity = "1";
      contentArea.scrollTop = 0;

      // Move <link> tags to <head>
      contentArea
        .querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')
        .forEach((link) => {
          if (
            !Array.from(
              document.head.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'),
            ).some((existing) => existing.href === link.href)
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
      document.dispatchEvent(new Event("docs:content-loaded"));

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
      if (request !== loadRequest || !contentArea.isConnected) return;
      const error = document.createElement("div");
      error.className = "docs-error";
      const icon = document.createElement("i");
      icon.className = "fas fa-exclamation-triangle";
      error.append(icon, document.createTextNode(" " + err.message));
      contentArea.replaceChildren(error);
      contentArea.style.opacity = "1";
    });
}

// ── Dropdown Toggle ──────────────────────────────────────────

function closeDropdown(dropdown: Element): void {
  dropdown.classList.remove("open");
  dropdown.querySelector(".docs-dropdown-toggle")?.setAttribute("aria-expanded", "false");
}

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
        .forEach((d) => {
          if (d !== dropdown) closeDropdown(d);
        });
      const open = dropdown.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
      return;
    }
    // Close all dropdowns on outside click
    document
      .querySelectorAll(".docs-dropdown.open")
      .forEach(closeDropdown);
  });
}

// ── Multi-Select ─────────────────────────────────────────────

function toggleSelection(
  item: HTMLAnchorElement,
  navItems: NodeListOf<HTMLAnchorElement>,
  sidebar: Element,
): void {
  const slug = item.dataset.docSlug ?? "";
  if (!slug) return;
  if (selectedSlugs.has(slug)) {
    selectedSlugs.delete(slug);
    item.classList.remove("selected");
  } else {
    selectedSlugs.add(slug);
    item.classList.add("selected");
  }
  updateSelectionBar(sidebar, navItems);
}

function clearSelection(
  navItems: NodeListOf<HTMLAnchorElement>,
  sidebar: Element,
): void {
  selectedSlugs.clear();
  navItems.forEach((i) => i.classList.remove("selected"));
  updateSelectionBar(sidebar, navItems);
}

function updateSelectionBar(
  sidebar: Element,
  navItems: NodeListOf<HTMLAnchorElement>,
): void {
  const toolbar = document.querySelector(".docs-toolbar");
  let bar = toolbar?.querySelector<HTMLElement>(".docs-selection-bar");
  if (selectedSlugs.size === 0) {
    bar?.remove();
    return;
  }
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "docs-selection-bar";
    bar.innerHTML =
      '<span class="docs-selection-count"></span>' +
      '<button class="docs-selection-dl-md" title="Download as .md">' +
      '<i class="fas fa-file-alt"></i> .md</button>' +
      '<button class="docs-selection-dl-pdf" title="Print as PDF">' +
      '<i class="fas fa-file-pdf"></i> .pdf</button>' +
      '<button class="docs-selection-clear" title="Clear selection">' +
      '<i class="fas fa-times"></i></button>';
    bar
      .querySelector(".docs-selection-dl-md")!
      .addEventListener("click", () => {
        downloadSelectedMd();
      });
    bar
      .querySelector(".docs-selection-dl-pdf")!
      .addEventListener("click", () => {
        downloadSelectedPdf(navItems);
      });
    bar
      .querySelector(".docs-selection-clear")!
      .addEventListener("click", () => {
        clearSelection(navItems, sidebar);
      });
    toolbar?.appendChild(bar);
  }
  bar.querySelector(".docs-selection-count")!.textContent =
    selectedSlugs.size + " selected";
}

function downloadSelectedMd(): void {
  const csrfMeta = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement | null;
  const csrf =
    csrfMeta?.value ?? document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "";
  fetch("/apps/docs/export-batch/", {
    method: "POST",
    headers: { "X-CSRFToken": csrf, "Content-Type": "application/json" },
    body: JSON.stringify({ slugs: Array.from(selectedSlugs) }),
  })
    .then((r) => r.blob())
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "scitex-docs-selected.md";
      a.click();
      URL.revokeObjectURL(a.href);
    });
}

function downloadSelectedPdf(navItems: NodeListOf<HTMLAnchorElement>): void {
  const slugs = Array.from(selectedSlugs);
  const fetches = slugs.map((s) =>
    fetch("/apps/docs/content/" + encodeURIComponent(s) + "/", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }).then((r) => r.text()),
  );
  Promise.all(fetches).then((pages) => {
    const labels = slugs.map((s) => {
      const item = Array.from(navItems).find((i) => i.dataset.docSlug === s);
      return item?.querySelector("span")?.textContent ?? s;
    });
    const combined = pages
      .map((html, i) => "<h1>" + labels[i] + "</h1>" + html)
      .join('<hr class="docs-print-page-break" />');
    openPrintWindow(combined);
  });
}

// ── Initialization ───────────────────────────────────────────

function initDocsWorkspace(): void {
  initDocsHtmlExport(PRINT_CSS);
  const workspace = document.querySelector<HTMLElement>(".docs-workspace");
  const sidebar = document.querySelector(".docs-sidebar");
  const contentArea = document.getElementById("docs-content-area");
  if (!workspace || !sidebar || !contentArea) return;

  const navItems =
    sidebar.querySelectorAll<HTMLAnchorElement>(".docs-nav-item");
  currentSlug = workspace.dataset.activeDoc ?? "";

  // Dropdown toggles and local document tools.
  initDropdowns();
  initDocsFilter(workspace);
  initDocsCopy(workspace);

  initDocsColumns(workspace, (slug) => {
    if (selectedSlugs.size > 0) clearSelection(navItems, sidebar);
    loadDocPage(slug, undefined, contentArea, sidebar, navItems);
  });
  document.getElementById("docs-export-page-pdf")?.addEventListener("click", () => {
    openPrintWindow(contentArea.innerHTML);
  });

  // Mobile cascade nav (section → page selects)
  initMobileCascade((slug) => loadDocPage(slug, undefined, contentArea, sidebar, navItems));

  // Global "All PDF" button
  const allPdfBtn = document.getElementById("docs-export-all-pdf");
  if (allPdfBtn) {
    allPdfBtn.onclick = () => {
      const slugs = Array.from(navItems).map((i) => i.dataset.docSlug ?? "");
      void printAllDocs(slugs);
    };
  }

  // Sync selection from DOM (triggered by context menu)
  document.addEventListener("docs:sync-selection", () => {
    selectedSlugs.clear();
    navItems.forEach((i) => {
      if (i.classList.contains("selected"))
        selectedSlugs.add(i.dataset.docSlug ?? "");
    });
    updateSelectionBar(sidebar, navItems);
  });

  // Sidebar click handlers (Ctrl+Click = multi-select, Click = navigate)
  navItems.forEach((item) => {
    item.addEventListener("click", (e: MouseEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        toggleSelection(item, navItems, sidebar);
      } else {
        if (selectedSlugs.size > 0) clearSelection(navItems, sidebar);
        const slug = item.dataset.docSlug ?? "";
        if (slug !== currentSlug) {
          loadDocPage(slug, undefined, contentArea, sidebar, navItems);
        }
      }
    });
  });

  // Parse hash: /docs/#slug or /docs/#slug--sectionId
  const hash = window.location.hash.replace("#", "");
  if (hash) {
    const parts = hash.split("--");
    const slugFromHash = parts[0];
    const anchorFromHash = parts[1] || undefined;
    const matchedItem = Array.from(navItems).find(
      (i) => i.dataset.docSlug === slugFromHash,
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
