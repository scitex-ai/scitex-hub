/**
 * File Tree Management Module
 * Thin wrapper around shared file tree functions
 */

import {
  loadFileTree as loadFileTreeShared,
  toggleFolder as toggleFolderShared,
} from "../file-tree";

/**
 * Load file tree from API and render it in sidebar - uses shared module
 */
export async function loadFileTree() {
  console.log("[loadFileTree] START - Loading file tree from sidebar");

  // Extract project info from page URL
  const pathParts = window.location.pathname.split("/").filter((x) => x);
  if (pathParts.length < 2) {
    console.log("[loadFileTree] Not enough path parts");
    return;
  }

  const username = pathParts[0];
  const slug = pathParts[1];
  console.log("[loadFileTree] Fetching tree for:", username + "/" + slug);

  // Use shared loadFileTree function
  await loadFileTreeShared(username, slug, "file-tree");
}

/**
 * Toggle folder expansion in file tree - uses shared module
 */
export function toggleFolder(folderId: string, event?: Event): boolean {
  console.log("[toggleFolder] Toggling folder:", folderId);
  toggleFolderShared(folderId, event);
  return false;
}
