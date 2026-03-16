/**
 * FigrecipeMountPoint — mounts the figrecipe React editor into a DOM element.
 *
 * Handles:
 *   1. React root creation
 *   2. Fetch override (API routing to /vis/api/figrecipe/)
 *   3. Event callback wiring to BridgeEventBus
 *   4. Cleanup on unmount
 */

import React from "react";
import { createRoot, Root } from "react-dom/client";
import { FigrecipeEditor } from "figrecipe-editor";
import { emitBridgeEvent, onBridgeEvent } from "./BridgeEventBus";

let root: Root | null = null;
let fetchOverrideInstalled = false;

/**
 * Figrecipe API endpoint prefixes that should be routed through Django.
 * Only these paths get rewritten — all other fetches pass through unchanged.
 */
const FIGRECIPE_API_PATHS = [
  "/preview",
  "/hitmap",
  "/update",
  "/save",
  "/restore",
  "/switch_theme",
  "/list_themes",
  "/download/",
  "/datatable/",
  "/get_axes_positions",
  "/update_axes_position",
  "/update_legend_position",
  "/update_label",
  "/update_call",
  "/get_labels",
  "/calls",
  "/stats/",
  "/api/files",
  "/api/switch",
  "/api/compose",
  "/api/delete",
  "/api/rename",
  "/api/file-tree",
  "/api/git/",
];

/**
 * Install fetch override to route figrecipe API calls through Django.
 * Converts figrecipe-specific paths like `/preview?recipe=...` to
 * `/vis/api/figrecipe/preview?recipe=...`.
 */
function installFetchOverride(): void {
  if (fetchOverrideInstalled) return;

  const originalFetch = window.fetch;
  window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
    if (typeof input === "string" && input.startsWith("/")) {
      // Only rewrite known figrecipe API paths
      const pathOnly = input.split("?")[0];
      const isFigrecipePath = FIGRECIPE_API_PATHS.some(
        (prefix) => pathOnly === prefix || pathOnly.startsWith(prefix),
      );
      if (isFigrecipePath) {
        input = `/apps/figrecipe/figrecipe${input}`;
      }
    }
    return originalFetch.call(window, input, init);
  };

  fetchOverrideInstalled = true;
}

export interface MountOptions {
  /** DOM element to mount into. */
  container: HTMLElement;
  /** Project working directory (resolved server-side). */
  workingDir?: string;
  /** Initial recipe path to open. */
  recipe?: string;
  /** Dark mode. */
  darkMode?: boolean;
}

/**
 * Mount the figrecipe editor into the given container.
 */
export function mountFigrecipeEditor(options: MountOptions): void {
  const { container, workingDir, recipe, darkMode } = options;

  // Install fetch override before React renders
  installFetchOverride();

  // Clean up previous mount if any
  if (root) {
    root.unmount();
    root = null;
  }

  root = createRoot(container);
  root.render(
    React.createElement(FigrecipeEditor, {
      apiBaseUrl: "/apps/figrecipe/figrecipe",
      workingDir,
      recipe,
      darkMode,
      onFileSelect: (path: string) => {
        emitBridgeEvent("figrecipe:fileSelect", { path });
      },
      onElementSelect: (elementId: string, bbox: any) => {
        emitBridgeEvent("figrecipe:elementSelect", { elementId, bbox });
      },
      onPropertyChange: (key: string, value: unknown) => {
        emitBridgeEvent("figrecipe:propertyChange", { key, value });
      },
      onDataChange: (columns: string[], rowCount: number) => {
        emitBridgeEvent("figrecipe:dataChange", { columns, rowCount });
      },
      onStatBracketAdd: (bracket: any) => {
        emitBridgeEvent("figrecipe:statBracketAdd", bracket);
      },
    }),
  );
}

/**
 * Switch the loaded recipe file (called from TS side).
 */
export function switchRecipeFile(path: string): void {
  // Import the store at runtime to avoid circular deps
  import("figrecipe-editor").then(({ useEditorStore }) => {
    const params = new URLSearchParams(window.location.search);
    params.set("recipe", path);
    params.set("mode", "embedded");
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, "", newUrl);

    // Trigger preview reload
    const store = useEditorStore.getState();
    store.loadPreview();
    store.loadHitmap();
    store.loadDatatable();
  });
}

/**
 * Unmount the figrecipe editor and clean up.
 */
export function unmountFigrecipeEditor(): void {
  if (root) {
    root.unmount();
    root = null;
  }
}
