/**
 * Monaco Editor Loader (Workspace Viewer)
 *
 * Thin wrapper around the shared monaco-init module.
 * Monaco is bundled locally — no CDN dependency.
 */

import { monaco } from "@/_lib/monaco-init";

let loaded = false;

/** Load Monaco editor, returning true if available. */
export function loadMonaco(): Promise<boolean> {
  if (loaded) return Promise.resolve(true);

  // monaco-init.ts handles everything synchronously at import time
  if (monaco) {
    loaded = true;
    return Promise.resolve(true);
  }

  // Should never reach here since monaco is bundled
  console.error("[MonacoLoader] Monaco not available after import");
  return Promise.resolve(false);
}
