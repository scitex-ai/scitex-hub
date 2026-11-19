// ── Mobile Cascade Nav (section → page dropdowns) ─────────
// Two labeled <select>s rendered server-side from docs_sections (same
// DOCS_PAGES source as the sidebar). Level 1 picks the section, level 2
// lists pages within it. Desktop keeps the sidebar; CSS shows this nav
// ≤767px only.

interface CascadePage {
  value: string;
  label: string;
}

const cascadePagesBySection = new Map<string, CascadePage[]>();
const cascadeSectionBySlug = new Map<string, string>();

function snapshotCascadeOptions(pageSelect: HTMLSelectElement): void {
  cascadePagesBySection.clear();
  cascadeSectionBySlug.clear();
  pageSelect.querySelectorAll("optgroup").forEach((group) => {
    const key = group.getAttribute("data-section") ?? "";
    if (!key) return;
    const pages: CascadePage[] = [];
    group.querySelectorAll("option").forEach((opt) => {
      pages.push({
        value: opt.value,
        label: opt.textContent?.trim() ?? opt.value,
      });
      cascadeSectionBySlug.set(opt.value, key);
    });
    cascadePagesBySection.set(key, pages);
  });
}

function populateCascadePages(
  sectionSelect: HTMLSelectElement,
  pageSelect: HTMLSelectElement,
  sectionKey: string,
): void {
  const pages = cascadePagesBySection.get(sectionKey) ?? [];
  pageSelect.textContent = "";
  pages.forEach((page) => {
    const opt = document.createElement("option");
    opt.value = page.value;
    opt.textContent = page.label;
    pageSelect.appendChild(opt);
  });
  pageSelect.disabled = pages.length === 0;
}

/** Keep both dropdowns in sync with the currently displayed doc page. */
export function syncMobileCascade(slug: string): void {
  const sectionSelect = document.getElementById(
    "docs-mobile-section",
  ) as HTMLSelectElement | null;
  const pageSelect = document.getElementById(
    "docs-mobile-page",
  ) as HTMLSelectElement | null;
  if (!sectionSelect || !pageSelect || !cascadePagesBySection.size) return;
  const sectionKey = cascadeSectionBySlug.get(slug);
  if (!sectionKey) return;
  if (sectionSelect.value !== sectionKey) {
    sectionSelect.value = sectionKey;
    populateCascadePages(sectionSelect, pageSelect, sectionKey);
  }
  if (pageSelect.value !== slug) pageSelect.value = slug;
}

export function initMobileCascade(navigate: (slug: string) => void): void {
  const sectionSelect = document.getElementById(
    "docs-mobile-section",
  ) as HTMLSelectElement | null;
  const pageSelect = document.getElementById(
    "docs-mobile-page",
  ) as HTMLSelectElement | null;
  if (!sectionSelect || !pageSelect) return;

  snapshotCascadeOptions(pageSelect);
  // Flatten to the active section's pages on init (optgroups are only the
  // no-JS fallback carrying the full section → page map).
  const initialSection =
    sectionSelect.value || sectionSelect.options[0]?.value || "";
  if (initialSection) {
    populateCascadePages(sectionSelect, pageSelect, initialSection);
    const initialSlug = document.querySelector<HTMLElement>(".docs-workspace")?.dataset.activeDoc;
    if (initialSlug) pageSelect.value = initialSlug;
  }

  sectionSelect.addEventListener("change", () => {
    const key = sectionSelect.value;
    populateCascadePages(sectionSelect, pageSelect, key);
    // Cascade: selecting a section navigates to its first page.
    const available = cascadePagesBySection.get(key) ?? [];
    const first = available.find((page) => Array.from(document.querySelectorAll<HTMLElement>(".docs-nav-item")).some((item) => item.dataset.docSlug === page.value && !item.hidden)) ?? available[0];
    if (first) {
      navigate(first.value);
    }
  });

  pageSelect.addEventListener("change", () => {
    if (pageSelect.value) {
      navigate(pageSelect.value);
    }
  });
}
