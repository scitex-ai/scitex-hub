/**
 * Loading a text file for the viewer, and what to show when it cannot load.
 *
 * A missing file used to open as an editable-looking "Editor" tab whose
 * content was the error text ("// Error loading file: ... HTTP 404"), so the
 * failure read as a real file (site audit 2026-09-14, D12). A failed load now
 * shows a not-found / error state in place of the editor, never text in it.
 */

export type TextLoad =
  | { kind: "ok"; content: string }
  | { kind: "not-found" }
  | { kind: "error"; message: string };

export type FetchLike = (url: string) => Promise<Response>;

/** Fetch a file's raw text; a 404 is "not-found", any other failure "error". */
export async function fetchTextFile(
  url: string,
  fetchImpl: FetchLike,
): Promise<TextLoad> {
  try {
    const response = await fetchImpl(url);
    if (response.status === 404) return { kind: "not-found" };
    if (!response.ok)
      return { kind: "error", message: `HTTP ${response.status}` };
    return { kind: "ok", content: await response.text() };
  } catch (err) {
    return { kind: "error", message: String(err) };
  }
}

export interface ViewerPanes {
  monacoContainer: HTMLElement;
  mediaContainer: HTMLElement;
  previewContainer: HTMLElement | null;
}

/**
 * Replace the editor with a read-only not-found / error state.
 * The editor pane is hidden, so nothing about the failure can be edited.
 */
export function showLoadFailure(
  panes: ViewerPanes,
  filePath: string,
  load: Exclude<TextLoad, { kind: "ok" }>,
): void {
  panes.monacoContainer.style.display = "none";
  if (panes.previewContainer) panes.previewContainer.style.display = "none";
  panes.mediaContainer.style.display = "block";

  const box = document.createElement("div");
  box.className = "ws-viewer-placeholder ws-viewer-load-failure";
  box.setAttribute("role", "status");
  box.dataset.viewerLoadFailure = load.kind;

  const icon = document.createElement("i");
  icon.className =
    load.kind === "not-found"
      ? "fas fa-file-circle-question"
      : "fas fa-triangle-exclamation";
  icon.setAttribute("aria-hidden", "true");

  const title = document.createElement("p");
  title.className = "ws-viewer-load-failure__title";
  title.textContent =
    load.kind === "not-found" ? "File not found" : "Could not load this file";

  const detail = document.createElement("p");
  detail.className = "ws-viewer-load-failure__detail";
  const name = document.createElement("code");
  name.textContent = filePath;
  detail.append(name);
  if (load.kind === "error") detail.append(` (${load.message})`);

  box.append(icon, title, detail);
  panes.mediaContainer.replaceChildren(box);
}
