/**
 * Hub Hash Router — handles #browse/{moduleName} URL fragments.
 *
 * When users click "View in Hub" from context menus, the URL includes
 * a hash like #browse/dev__owner__repo. This module processes that hash
 * on page load and switches to the correct project.
 */

import { hubPost } from "./hub-api";
import { pushProjectUrl } from "./hub-url";

export function handleBrowseHash(
  selectProject: (id: string) => Promise<void>,
): void {
  const hash = window.location.hash;
  if (!hash.startsWith("#browse/")) return;

  const moduleName = hash.slice("#browse/".length);
  if (!moduleName) return;

  // Parse dev__owner__repo pattern
  if (moduleName.startsWith("dev__")) {
    const parts = moduleName.slice("dev__".length).split("__");
    if (parts.length >= 2) {
      const owner = parts[0];
      const repo = parts.slice(1).join("__");
      selectProjectByOwnerSlug(owner, repo);
      return;
    }
  }

  // Regular module — look up in project selector by name
  const option = document.querySelector(
    `select option[data-module="${moduleName}"]`,
  ) as HTMLOptionElement | null;
  if (option?.value) {
    selectProject(option.value);
    cleanHash();
  }
}

async function selectProjectByOwnerSlug(
  owner: string,
  slug: string,
): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";

  const data = await hubPost("/hub/api/select-project/", { owner, slug });
  if (!data?.success) {
    content.style.opacity = "1";
    return;
  }

  content.innerHTML = data.html;
  content.style.opacity = "1";

  if (data.owner && data.project_slug) {
    (window as any).SCITEX_PROJECT_DATA = {
      owner: data.owner,
      slug: data.project_slug,
    };
    pushProjectUrl();
  }

  cleanHash();
}

function cleanHash(): void {
  history.replaceState(null, "", window.location.pathname);
}
