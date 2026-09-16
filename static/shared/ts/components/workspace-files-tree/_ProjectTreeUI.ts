/**
 * Workspace Files Tree - Project UI wiring
 *
 * The file tree is the default Project UI on every project entry point
 * (My Projects, Public Projects, /<owner>/<slug>/, /tree/ and /blob/ deep
 * links — operator 2026-09-14). The server renders the mount with:
 *
 *   data-read-only="true"  viewer cannot write  -> TreeConfig.readOnly
 *   data-focus-path="a/b"  /tree/<branch>/a/b    -> expand that folder
 *   data-open-file="a/b.py" /blob/a/b.py         -> open it in the viewer
 *
 * and, for an empty project, a sibling [data-tree-empty] block ("No files
 * yet", plus Upload / New file when the viewer can write).
 */

import type { WorkspaceFilesTree } from "./WorkspaceFilesTree";
import { FileUpload } from "./_handlers/FileUpload";
import { getCsrfToken } from "../../utils/csrf";

export function isReadOnlyMount(pane: HTMLElement): boolean {
  return pane.dataset.readOnly === "true";
}

/** Expand a /tree/ folder, or reveal and open a /blob/ file. */
export async function applyDeepLink(
  pane: HTMLElement,
  tree: WorkspaceFilesTree,
): Promise<void> {
  const folder = pane.dataset.focusPath;
  const file = pane.dataset.openFile;
  if (folder) await tree.focusDirectory(folder, false);
  if (!file) return;
  await tree.expandPath(file);
  // Let every DOMContentLoaded handler finish first: the viewer registers
  // its file-open listener in its own handler (workspace-viewer/init.ts).
  window.setTimeout(() => {
    document.dispatchEvent(
      new CustomEvent("file-open", { detail: { path: file } }),
    );
  }, 0);
}

/** Show/hide the empty state as the tree gains items; wire its buttons. */
export function wireEmptyState(
  pane: HTMLElement,
  tree: WorkspaceFilesTree,
  project: { ownerUsername: string; projectSlug: string },
): void {
  const empty =
    pane.parentElement?.querySelector<HTMLElement>("[data-tree-empty]");
  if (!empty) return;

  const sync = (): void => {
    const hasItems = pane.querySelector(".wft-item:not(.wft-root)") !== null;
    empty.hidden = hasItems;
  };
  new MutationObserver(sync).observe(pane, { childList: true, subtree: true });
  sync();

  const input = empty.querySelector<HTMLInputElement>(
    "[data-tree-upload-input]",
  );
  const uploader = new FileUpload(
    { mode: "hub", containerId: pane.id, ...project },
    getCsrfToken,
    () => tree.refresh(),
  );
  input?.addEventListener("change", () => {
    if (input.files?.length) void uploader.uploadFiles(input.files, "");
  });
  empty.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>(
      "[data-tree-empty-action]",
    );
    if (!btn) return;
    if (btn.dataset.treeEmptyAction === "upload") input?.click();
    else void tree.runAction("new-file", "");
  });
}
