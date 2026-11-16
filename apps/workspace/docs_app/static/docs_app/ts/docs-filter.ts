/** Fuzzy document navigation, using the SDK matcher and the existing hierarchy. */
import { mountFilterFields } from "@scitex/sdk/ui/ts/app/filter-field";
import "@scitex/sdk/ui/css/app/filter-field.css";
import { fuzzyScore } from "@scitex/sdk/ui/ts/app/project-selector/fuzzy";

function highlight(label: HTMLElement, text: string, query: string): void {
  label.replaceChildren();
  const lower = text.toLowerCase();
  const hits = new Set<number>();
  let from = 0;
  if (query && fuzzyScore(query, text) !== null) {
    for (const char of query.toLowerCase()) {
      const index = lower.indexOf(char, from);
      for (let i = 0; i < char.length; i++) hits.add(index + i);
      from = index + char.length;
    }
  }
  for (let index = 0; index < text.length; index++) {
    if (hits.has(index)) {
      const mark = document.createElement("mark");
      mark.textContent = text[index];
      label.append(mark);
    } else label.append(document.createTextNode(text[index]));
  }
}

export function initDocsFilter(workspace: HTMLElement): void {
  mountFilterFields(workspace);
  const input = workspace.querySelector<HTMLInputElement>("#docs-filter-input");
  const show = workspace.querySelector<HTMLInputElement>("#docs-filter-show-hidden");
  const summary = workspace.querySelector<HTMLElement>("#docs-filter-summary");
  const options = workspace.querySelector<HTMLElement>("#docs-filter-options");
  if (!input || !show || !summary || !options) return;
  input.setAttribute("aria-describedby", "docs-filter-summary");
  const pages = Array.from(workspace.querySelectorAll<HTMLAnchorElement>(".docs-nav-item"));
  const labels = new Map(pages.map((page) => [page, page.querySelector("span")?.textContent?.trim() ?? ""]));
  const categories = Array.from(workspace.querySelectorAll<HTMLButtonElement>(".docs-category"));
  const categoryLabels = new Map(categories.map((category) => [category, category.textContent?.trim() ?? ""]));

  function apply(): void {
    const query = input!.value.trim();
    if (!query) show!.checked = false;
    const counts = new Map<string, { total: number; matched: number }>();
    let matched = 0;
    workspace.classList.toggle("docs-has-filter", !!query);
    pages.forEach((page) => {
      const group = page.closest<HTMLElement>(".docs-page-group");
      const key = group?.dataset.docGroup ?? "";
      const category = categories.find((item) => item.dataset.docCategory === key);
      const text = labels.get(page) ?? "";
      const fields = [text, page.dataset.docSlug ?? "", category ? categoryLabels.get(category) ?? "" : ""];
      const match = fields.some((field) => fuzzyScore(query, field) !== null);
      const count = counts.get(key) ?? { total: 0, matched: 0 };
      count.total++;
      if (match) { count.matched++; matched++; }
      counts.set(key, count);
      page.hidden = !match && !show!.checked;
      page.classList.toggle("docs-filtered-out", !match);
      const label = page.querySelector<HTMLElement>("span");
      if (label) highlight(label, text, query);
    });
    categories.forEach((category) => {
      const count = counts.get(category.dataset.docCategory ?? "") ?? { total: 0, matched: 0 };
      let badge = category.querySelector<HTMLElement>(".docs-match-count");
      if (!badge) {
        badge = document.createElement("span"); badge.className = "docs-match-count"; badge.setAttribute("aria-hidden", "true"); category.append(badge);
      }
      badge.textContent = `${count.matched}/${count.total}`;
      badge.hidden = !query;
      category.title = categoryLabels.get(category) ?? "";
      category.disabled = !!query && count.matched === 0 && !show!.checked;
    });
    const pageSelect = workspace.querySelector<HTMLSelectElement>("#docs-mobile-page");
    const activeSlug = pages.find((page) => page.classList.contains("active"))?.dataset.docSlug;
    pageSelect?.querySelectorAll("option").forEach((option) => {
      const page = pages.find((item) => item.dataset.docSlug === option.value);
      const excluded = !!page?.classList.contains("docs-filtered-out");
      option.hidden = excluded && !show!.checked && option.value !== activeSlug;
      option.disabled = excluded && !show!.checked && option.value !== activeSlug;
    });
    workspace.querySelector<HTMLSelectElement>("#docs-mobile-section")?.querySelectorAll("option").forEach((option) => {
      option.disabled = !!query && (counts.get(option.value)?.matched ?? 0) === 0 && !show!.checked;
    });
    options!.hidden = !query;
    const active = pages.find((page) => page.classList.contains("active"));
    summary!.textContent = `${matched} of ${pages.length} documents match` + (active?.classList.contains("docs-filtered-out") ? ". Open page is outside the filter." : "");
  }
  input.addEventListener("input", apply);
  show.addEventListener("change", apply);
  document.addEventListener("docs:navigation", apply);
  document.addEventListener("docs:content-loaded", apply);
  apply();
}
