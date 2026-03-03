/**
 * Docs workspace — sidebar navigation, AJAX page loading, section folding,
 * export buttons (Markdown + PDF).
 *
 * Extracted from docs_partial.html inline <script>.
 * Reads initial state from data-active-doc attribute on .docs-workspace.
 */

function initDocsWorkspace(): void {
  const workspace = document.querySelector<HTMLElement>(".docs-workspace");
  const sidebar = document.querySelector(".docs-sidebar");
  const contentArea = document.getElementById("docs-content-area");
  if (!workspace || !sidebar || !contentArea) return;

  const navItems =
    sidebar.querySelectorAll<HTMLAnchorElement>(".docs-nav-item");
  let currentSlug = workspace.dataset.activeDoc ?? "";

  /** Convert api-sections into folded cards with toggle buttons. */
  function foldSections(anchorId?: string): void {
    const sections = contentArea!.querySelectorAll(".api-section");
    sections.forEach((section) => {
      if (section.querySelector(".api-section-toggle")) return;

      const h2 = section.querySelector("h2");
      if (!h2) return;

      // Collect all anchor IDs from preceding spans and section itself
      const anchorIds: string[] = [];
      if (section.id) anchorIds.push(section.id);
      let prev = section.previousElementSibling;
      while (prev && prev.tagName === "SPAN" && prev.id) {
        anchorIds.push(prev.id);
        prev = prev.previousElementSibling;
      }

      // Pick the best anchor ID: first preceding span (closest to section)
      const linkAnchor = anchorIds[1] || anchorIds[0] || "";

      // Extract title text excluding .anchor-link elements
      const h2Clone = h2.cloneNode(true) as HTMLElement;
      h2Clone.querySelectorAll(".anchor-link").forEach((el) => el.remove());
      const titleText = h2Clone.textContent?.trim() ?? "";

      const toggle = document.createElement("button");
      toggle.className = "api-section-toggle";
      toggle.innerHTML =
        '<i class="fas fa-chevron-right fold-icon"></i> ' +
        '<span class="api-section-title">' +
        titleText +
        "</span>";

      // Add share link button (clip icon only)
      if (linkAnchor) {
        const linkBtn = document.createElement("a");
        linkBtn.className = "api-section-link";
        linkBtn.href = "#" + currentSlug + "--" + linkAnchor;
        linkBtn.title = "Copy link to this section";
        linkBtn.innerHTML = '<i class="fas fa-link"></i>';
        linkBtn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          const url =
            window.location.origin +
            "/docs/#" +
            currentSlug +
            "--" +
            linkAnchor;
          navigator.clipboard.writeText(url).then(() => {
            linkBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
              linkBtn.innerHTML = '<i class="fas fa-link"></i>';
            }, 1500);
          });
        });
        toggle.appendChild(linkBtn);
      }

      const body = document.createElement("div");
      body.className = "api-section-body";
      while (section.firstChild) {
        body.appendChild(section.firstChild);
      }
      section.appendChild(toggle);
      section.appendChild(body);

      toggle.addEventListener("click", (e) => {
        if ((e.target as HTMLElement).closest(".api-section-link")) return;
        section.classList.toggle("open");
        // Update URL hash when card is opened
        if (section.classList.contains("open") && linkAnchor) {
          history.replaceState(null, "", "#" + currentSlug + "--" + linkAnchor);
        }
      });

      // Auto-open if anchor matches any of this section's IDs
      if (anchorId && anchorIds.includes(anchorId)) {
        section.classList.add("open");
        setTimeout(
          () => section.scrollIntoView({ behavior: "smooth", block: "start" }),
          100,
        );
      }
    });
  }

  const PRINT_CSS =
    "body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#222}" +
    "pre{background:#f5f5f5;padding:1rem;overflow-x:auto;border-radius:4px}" +
    "code{font-family:monospace}h1,h2,h3{margin-top:1.5rem}" +
    "table{border-collapse:collapse;width:100%}" +
    "th,td{border:1px solid #ddd;padding:8px;text-align:left}";

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

  /** Per-section export buttons (injected after AJAX load). */
  function injectSectionExportButtons(slug: string): void {
    if (contentArea!.querySelector(".docs-section-export")) return;
    const bar = document.createElement("div");
    bar.className = "docs-section-export";
    bar.innerHTML =
      '<a href="/docs/export/' +
      slug +
      '/" class="docs-export-btn" title="Download this page as Markdown">' +
      '<i class="fas fa-file-alt"></i> .md</a>' +
      '<button class="docs-export-btn docs-section-pdf-btn" title="Print this page as PDF">' +
      '<i class="fas fa-file-pdf"></i> .pdf</button>';
    const pdfBtn = bar.querySelector<HTMLButtonElement>(
      ".docs-section-pdf-btn",
    );
    if (pdfBtn) {
      pdfBtn.onclick = () => openPrintWindow(contentArea!.innerHTML);
    }
    contentArea!.insertBefore(bar, contentArea!.firstChild);
  }

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

  function loadDocPage(slug: string, anchorId?: string): void {
    if (!slug) return;
    currentSlug = slug;

    // Update URL hash to reflect current page
    const hashValue = anchorId ? slug + "--" + anchorId : slug;
    history.replaceState(null, "", "#" + hashValue);

    // Update active state in sidebar
    navItems.forEach((item) => {
      item.classList.toggle("active", item.dataset.slug === slug);
    });

    // Show loading
    contentArea!.style.opacity = "0.5";

    fetch("/docs/content/" + slug + "/", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((response) => {
        if (!response.ok) throw new Error("Failed to load: " + response.status);
        return response.text();
      })
      .then((html) => {
        contentArea!.innerHTML = html;
        contentArea!.style.opacity = "1";
        contentArea!.scrollTop = 0;
        // Move any <link /> tags to <head>
        const links = contentArea!.querySelectorAll<HTMLLinkElement>(
          'link[rel="stylesheet"]',
        );
        links.forEach((link) => {
          if (
            !document.querySelector(
              'link[href="' + link.getAttribute("href") + '"]',
            )
          ) {
            document.head.appendChild(link.cloneNode(true));
          }
          link.remove();
        });
        // Execute inline scripts (preserve type="module" for Vite)
        const scripts = contentArea!.querySelectorAll("script");
        scripts.forEach((oldScript) => {
          const newScript = document.createElement("script");
          if (oldScript.type) newScript.type = oldScript.type;
          if (oldScript.src) {
            newScript.src = oldScript.src;
          } else {
            newScript.textContent = oldScript.textContent;
          }
          oldScript.parentNode?.replaceChild(newScript, oldScript);
        });
        // Fold sections into collapsible cards
        foldSections(anchorId);
        // Inject per-section export buttons
        injectSectionExportButtons(slug);
      })
      .catch((err: Error) => {
        contentArea!.innerHTML =
          '<div class="docs-error"><i class="fas fa-exclamation-triangle"></i> ' +
          err.message +
          "</div>";
        contentArea!.style.opacity = "1";
      });
  }

  // Sidebar click handlers
  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      loadDocPage(item.dataset.slug ?? "");
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
      loadDocPage(currentSlug, anchorFromHash);
    } else {
      loadDocPage(currentSlug, hash);
    }
  } else {
    loadDocPage(currentSlug);
  }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDocsWorkspace);
} else {
  initDocsWorkspace();
}
