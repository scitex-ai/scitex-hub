/**
 * Project context — the single reader for the active project id in Scholar.
 *
 * Normalization contract: every Scholar module resolves the project through
 * `getSelectedProjectId()` here, never by touching sessionStorage directly.
 * Resolution order (first hit wins, result is persisted for other readers):
 *   1. sessionStorage["scholar_selected_project_id"] (written by the shared
 *      header selector and the Scholar picker on change)
 *   2. `?project=<id>` URL param (deep links, e.g. from My Projects)
 *   3. shared header selector button `data-active-project-id`
 *   4. Scholar's own `<select id="project-selector">` current value
 *      (server-rendered `selected` fires no change event — this is the case
 *      that used to report "No project selected" with a project on screen)
 *
 * A project id of "" / "all" means user-level scope (all projects).
 * Returns null only when no project context exists anywhere.
 */
export const PROJECT_STORAGE_KEY = "scholar_selected_project_id";

function fromUrl(): string | null {
  try {
    const id = new URLSearchParams(window.location.search).get("project");
    return id && id.trim() !== "" ? id : null;
  } catch {
    return null;
  }
}

function fromHeaderButton(): string | null {
  const btn = document.querySelector(
    ".project-selector-btn[data-active-project-id]",
  ) as HTMLElement | null;
  const id = btn?.dataset?.activeProjectId;
  return id && id.trim() !== "" ? id : null;
}

function fromScholarPicker(): string | null {
  const sel = document.getElementById(
    "project-selector",
  ) as HTMLSelectElement | null;
  return sel && sel.value && sel.value.trim() !== "" ? sel.value : null;
}

export function getSelectedProjectId(): string | null {
  const stored = sessionStorage.getItem(PROJECT_STORAGE_KEY);
  if (stored && stored.trim() !== "") return stored;

  const resolved = fromUrl() ?? fromHeaderButton() ?? fromScholarPicker();
  if (resolved) {
    try {
      sessionStorage.setItem(PROJECT_STORAGE_KEY, resolved);
    } catch {
      /* storage may be unavailable; callers still get the value */
    }
  }
  return resolved;
}

/** Explicitly set (or clear, with null) the active project id. */
export function setSelectedProjectId(projectId: string | null): void {
  try {
    if (projectId && projectId.trim() !== "") {
      sessionStorage.setItem(PROJECT_STORAGE_KEY, projectId);
    } else {
      sessionStorage.removeItem(PROJECT_STORAGE_KEY);
    }
  } catch {
    /* ignore */
  }
}
