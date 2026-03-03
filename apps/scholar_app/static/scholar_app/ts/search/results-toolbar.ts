/**
 * Results Toolbar Module
 *
 * Handles toolbar functionality for search results:
 * - Abstract toggle
 * - Save selected papers
 * - Open URLs
 * - Export BibTeX
 * - Ctrl+C to copy BibTeX
 */
/**
 * Get data from selected paper cards
 */
export function getSelectedPapers() {
    const selected = [];
    document.querySelectorAll(".result-card").forEach((card) => {
        const checkbox = card.querySelector(".paper-select");
        if (checkbox && checkbox.checked) {
            const titleEl = card.querySelector(".result-title a");
            const metaEl = card.querySelector(".result-meta");
            const snippetEl = card.querySelector(".result-snippet");
            const yearEl = card.querySelector(".year-badge");
            selected.push({
                title: titleEl?.textContent?.trim() || "Unknown",
                url: titleEl?.href || "",
                authors: metaEl?.querySelector(".authors")?.textContent?.trim() || "",
                journal: metaEl?.querySelector(".journal-badge")?.textContent?.trim() || "",
                year: yearEl?.textContent?.trim() || "",
                abstract: snippetEl?.dataset?.fullAbstract ||
                    snippetEl?.textContent?.trim() ||
                    "",
                doi: card.dataset?.doi || "",
                source: metaEl?.querySelector(".source-badge")?.textContent?.trim() || "",
            });
        }
    });
    return selected;
}
/**
 * Generate a BibTeX key from paper data
 */
export function generateBibtexKey(paper) {
    const firstAuthor = (paper.authors || "unknown").split(",")[0].split(" ").pop() || "unknown";
    const year = paper.year || "XXXX";
    const titleWord = (paper.title || "untitled")
        .split(" ")[0]
        .toLowerCase()
        .replace(/[^a-z]/g, "");
    return `${firstAuthor.toLowerCase()}${year}${titleWord}`;
}
/**
 * Generate BibTeX entry for a paper
 */
export function generateBibtexEntry(paper, includeAbstract = false) {
    const key = generateBibtexKey(paper);
    const authors = paper.authors || "Unknown";
    const title = paper.title || "Unknown";
    const journal = paper.journal?.replace(/\s*\(IF.*\)/, "") || "";
    const year = paper.year || "";
    const doi = paper.doi || "";
    const abstract = paper.abstract || "";
    let entry = `@article{${key},\n`;
    entry += `  author = {${authors}},\n`;
    entry += `  title = {${title}},\n`;
    if (journal)
        entry += `  journal = {${journal}},\n`;
    if (year)
        entry += `  year = {${year}},\n`;
    if (doi)
        entry += `  doi = {${doi}},\n`;
    if (includeAbstract && abstract) {
        entry += `  abstract = {${abstract.substring(0, 500)}${abstract.length > 500 ? "..." : ""}},\n`;
    }
    entry += `}`;
    return entry;
}
/**
 * Generate JSON export for papers
 */
export function generateJsonExport(papers) {
    return JSON.stringify(papers, null, 2);
}
/**
 * Generate plain text export for papers
 */
export function generateTextExport(papers) {
    return papers
        .map((paper, index) => {
        const lines = [`[${index + 1}] ${paper.title || "Unknown"}`];
        if (paper.authors)
            lines.push(`Authors: ${paper.authors}`);
        if (paper.journal)
            lines.push(`Journal: ${paper.journal}`);
        if (paper.year)
            lines.push(`Year: ${paper.year}`);
        if (paper.doi)
            lines.push(`DOI: ${paper.doi}`);
        if (paper.url)
            lines.push(`URL: ${paper.url}`);
        if (paper.abstract) {
            const truncatedAbstract = paper.abstract.length > 300
                ? paper.abstract.substring(0, 300) + "..."
                : paper.abstract;
            lines.push(`Abstract: ${truncatedAbstract}`);
        }
        return lines.join("\n");
    })
        .join("\n\n---\n\n");
}
/**
 * Export papers in specified format
 */
export function exportPapers(format) {
    const papers = getSelectedPapers();
    if (papers.length === 0) {
        alert("No papers selected. Click on papers to select them.");
        return;
    }
    let content;
    let filename;
    let mimeType;
    const dateStr = new Date().toISOString().slice(0, 10);
    switch (format) {
        case "bibtex":
            content = papers.map((p) => generateBibtexEntry(p, true)).join("\n\n");
            filename = `scitex_export_${dateStr}.bib`;
            mimeType = "text/plain";
            break;
        case "json":
            content = generateJsonExport(papers);
            filename = `scitex_export_${dateStr}.tson`;
            mimeType = "application/json";
            break;
        case "text":
            content = generateTextExport(papers);
            filename = `scitex_export_${dateStr}.txt`;
            mimeType = "text/plain";
            break;
    }
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
/**
 * Show temporary feedback message
 */
export function showCopyFeedback(message) {
    const existing = document.querySelector(".bibtex-copy-feedback");
    if (existing)
        existing.remove();
    const feedback = document.createElement("div");
    feedback.className = "bibtex-copy-feedback";
    feedback.textContent = message;
    document.body.appendChild(feedback);
    setTimeout(() => {
        feedback.style.opacity = "0";
        setTimeout(() => feedback.remove(), 300);
    }, 2000);
}
/**
 * Update toolbar button states based on selection
 */
export function updateToolbarState() {
    const selectedCount = document.querySelectorAll(".result-card .paper-select:checked").length;
    // Update toolbar buttons
    const buttons = [
        "saveSelectedBtn",
        "openUrlsBtn",
        "exportSelectedBibtex",
        "downloadSelectedPdfs",
    ];
    buttons.forEach((id) => {
        const btn = document.getElementById(id);
        if (btn)
            btn.disabled = selectedCount === 0;
    });
    // Update fixed selection action bar
    const actionBar = document.getElementById("selectionActionBar");
    const countEl = document.getElementById("selectedCount");
    if (actionBar) {
        if (selectedCount > 0) {
            actionBar.classList.add("visible");
            if (countEl)
                countEl.textContent = String(selectedCount);
        }
        else {
            actionBar.classList.remove("visible");
        }
    }
}
/**
 * Initialize abstract toggle button
 */
function initAbstractToggle() {
    const btn = document.getElementById("abstractToggleBtn");
    btn?.addEventListener("click", function () {
        const modes = ["truncated", "full", "none"];
        const currentMode = this.dataset.mode || "truncated";
        const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
        const nextMode = modes[nextIndex];
        this.dataset.mode = nextMode;
        this.textContent = "Abstract: " + (nextMode === "none" ? "no" : nextMode);
        document.querySelectorAll(".result-snippet").forEach((el) => {
            const elem = el;
            if (nextMode === "none") {
                elem.style.display = "none";
            }
            else if (nextMode === "full") {
                elem.style.display = "block";
                elem.classList.add("expanded");
                elem.dataset.expanded = "true";
            }
            else {
                elem.style.display = "block";
                elem.classList.remove("expanded");
                elem.dataset.expanded = "false";
            }
        });
    });
}
/**
 * Initialize save selected button
 */
function initSaveSelected() {
    document.getElementById("saveSelectedBtn")?.addEventListener("click", () => {
        const papers = getSelectedPapers();
        if (papers.length === 0) {
            alert("No papers selected. Click on papers to select them.");
            return;
        }
        const saved = JSON.parse(localStorage.getItem("scitex_saved_papers") || "[]");
        const newPapers = papers.filter((p) => !saved.some((s) => s.title === p.title));
        saved.push(...newPapers);
        localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
        alert(`Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`);
    });
}
/**
 * Initialize open URLs button
 */
function initOpenUrls() {
    document.getElementById("openUrlsBtn")?.addEventListener("click", () => {
        const papers = getSelectedPapers();
        if (papers.length === 0) {
            alert("No papers selected. Click on papers to select them.");
            return;
        }
        if (papers.length > 10) {
            if (!confirm(`Open ${papers.length} URLs? This may be blocked by your browser.`))
                return;
        }
        papers.forEach((paper, i) => {
            if (paper.url && paper.url !== "#") {
                setTimeout(() => window.open(paper.url, "_blank"), i * 100);
            }
        });
    });
}
/**
 * Initialize BibTeX export button
 */
function initBibtexExport() {
    document
        .getElementById("exportSelectedBibtex")
        ?.addEventListener("click", () => {
        const papers = getSelectedPapers();
        if (papers.length === 0) {
            alert("No papers selected. Click on papers to select them.");
            return;
        }
        const bibtexContent = papers
            .map((p) => generateBibtexEntry(p, true))
            .join("\n\n");
        const blob = new Blob([bibtexContent], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `scitex_export_${new Date().toISOString().slice(0, 10)}.bib`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}
/**
 * Initialize Ctrl+C to copy BibTeX
 */
function initCopyShortcut() {
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "c") {
            const selection = window.getSelection();
            if (selection && selection.toString().trim().length > 0) {
                return; // Let browser handle normal text copy
            }
            const papers = getSelectedPapers();
            if (papers.length === 0) {
                return;
            }
            e.preventDefault();
            const bibtexContent = papers
                .map((p) => generateBibtexEntry(p, false))
                .join("\n\n");
            navigator.clipboard
                .writeText(bibtexContent)
                .then(() => {
                showCopyFeedback(`Copied ${papers.length} BibTeX ${papers.length === 1 ? "entry" : "entries"} to clipboard`);
            })
                .catch((err) => {
                console.error("Failed to copy BibTeX:", err);
            });
        }
    });
}
/**
 * Initialize selection change listener
 */
function initSelectionListener() {
    document.addEventListener("change", (e) => {
        const target = e.target;
        if (target.classList.contains("paper-select")) {
            updateToolbarState();
        }
    });
}
/**
 * Initialize all toolbar functionality
 */
export function initResultsToolbar() {
    initAbstractToggle();
    initSaveSelected();
    initOpenUrls();
    initBibtexExport();
    initCopyShortcut();
    initSelectionListener();
    updateToolbarState();
}
// Auto-initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", initResultsToolbar);
//# sourceMappingURL=results-toolbar.ts.map
