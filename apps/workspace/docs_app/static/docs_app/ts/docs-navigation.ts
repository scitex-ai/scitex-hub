/** Two stable documentation navigation columns, using server-owned groups. */
import { syncDocsExportScope } from "./docs-export-scope";

let root: HTMLElement | null = null;
const lastPage = new Map<string, string>();

export function syncDocsColumns(slug: string): void {
  if (!root) return;
  const pages = Array.from(root.querySelectorAll<HTMLAnchorElement>(".docs-nav-item"));
  const page = pages.find((item) => item.dataset.docSlug === slug);
  const group = page?.closest<HTMLElement>(".docs-page-group");
  const category = group?.dataset.docGroup;
  if (!page || !category) return;
  lastPage.set(category, slug);
  root.querySelectorAll<HTMLElement>(".docs-page-group").forEach((item) => {
    item.hidden = item.dataset.docGroup !== category;
  });
  root.querySelectorAll<HTMLButtonElement>(".docs-category").forEach((item) => {
    const active = item.dataset.docCategory === category;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "true");
    else item.removeAttribute("aria-current");
  });
  const title = page.querySelector("span")?.textContent?.trim() ?? slug;
  const heading = root.querySelector("#docs-page-title");
  if (heading) heading.textContent = title;
  syncDocsExportScope(slug, undefined, root);
  document.dispatchEvent(new Event("docs:navigation"));
}

export function initDocsColumns(workspace: HTMLElement, navigate: (slug: string) => void): void {
  root = workspace;
  lastPage.clear();
  workspace.querySelectorAll<HTMLButtonElement>(".docs-category").forEach((button) => {
    button.addEventListener("click", () => {
      const category = button.dataset.docCategory ?? "";
      // Re-selecting a category must not reset the page or scroll position.
      if (button.classList.contains("active")) return;
      const group = Array.from(workspace.querySelectorAll<HTMLElement>(".docs-page-group"))
        .find((item) => item.dataset.docGroup === category);
      const pages = Array.from(group?.querySelectorAll<HTMLElement>(".docs-nav-item") ?? []).filter((page) => !page.hidden);
      const remembered = pages.find((page) => page.dataset.docSlug === lastPage.get(category));
      const slug = (remembered ?? pages[0])?.dataset.docSlug;
      if (slug) navigate(slug);
    });
  });
}
