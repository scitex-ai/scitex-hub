/**
 * VisEditorBridge — connects figrecipe bridge events to existing TS managers.
 *
 * Listens for CustomEvents emitted by the React bridge and calls
 * the appropriate workspace manager methods.
 */

import { onBridgeEvent } from "./BridgeEventBus";
import { switchRecipeFile } from "./FigrecipeMountPoint";

/** Cleanup functions for event subscriptions. */
const cleanups: Array<() => void> = [];

/**
 * Wire bridge events to the VisEditor instance.
 * Call this after VisEditor is initialized.
 */
export function wireVisEditorBridge(visEditor: any): void {
  // Clean up any previous wiring
  unwireVisEditorBridge();

  // React → TS: File selected in figrecipe
  cleanups.push(
    onBridgeEvent("figrecipe:fileSelect", ({ path }) => {
      console.log("[Bridge] figrecipe file selected:", path);
      visEditor.treeSyncCoordinator?.syncTreeToFigure(path);
    }),
  );

  // React → TS: Element selected on canvas
  cleanups.push(
    onBridgeEvent("figrecipe:elementSelect", ({ elementId, bbox }) => {
      console.log("[Bridge] figrecipe element selected:", elementId);
      visEditor.propertiesManager?.updateSelection(elementId, bbox);
    }),
  );

  // React → TS: Property changed
  cleanups.push(
    onBridgeEvent("figrecipe:propertyChange", ({ key, value }) => {
      console.log("[Bridge] figrecipe property changed:", key, value);
      visEditor.updateStatusBar?.(`Property ${key} updated`);
    }),
  );

  // React → TS: Data changed
  cleanups.push(
    onBridgeEvent("figrecipe:dataChange", ({ columns, rowCount }) => {
      console.log(
        "[Bridge] figrecipe data changed:",
        columns.length,
        "cols,",
        rowCount,
        "rows",
      );
      visEditor.updateStatusBar?.(
        `Data: ${columns.length} columns, ${rowCount} rows`,
      );
    }),
  );

  // React → TS: Stat bracket added
  cleanups.push(
    onBridgeEvent("figrecipe:statBracketAdd", (bracket) => {
      console.log("[Bridge] figrecipe stat bracket added:", bracket.bracket_id);
      visEditor.updateStatusBar?.(`Stat bracket added: ${bracket.stars}`);
    }),
  );

  // TS → React: Switch file (replaces postMessage)
  // File tree clicks are intercepted and routed here
  document.addEventListener("click", handleFileTreeClick);
  cleanups.push(() => {
    document.removeEventListener("click", handleFileTreeClick);
  });
}

const RECIPE_EXTS = [".yaml", ".yml"];

function handleFileTreeClick(e: Event): void {
  const link = (e.target as Element)?.closest("[data-file-path]");
  if (!link) return;

  const path = link.getAttribute("data-file-path") || "";
  const ext = path.substring(path.lastIndexOf(".")).toLowerCase();

  if (RECIPE_EXTS.includes(ext)) {
    e.preventDefault();
    e.stopPropagation();
    switchRecipeFile(path);
  }
}

/**
 * Remove all bridge event subscriptions.
 */
export function unwireVisEditorBridge(): void {
  for (const cleanup of cleanups) {
    cleanup();
  }
  cleanups.length = 0;
}

/**
 * Run a stat test via figrecipe's API and render the bracket.
 * Delegates to figrecipe._django handlers.
 */
export async function runStatAndRenderBracket(
  testName: string,
  groups: Array<{ label: string; values: number[] }>,
  axIndex: number = 0,
  groupPositions?: { x1: number; x2: number },
): Promise<{
  result: any;
  annotation: any;
  bracket_id: string;
  preview: string;
}> {
  // Run stat test via figrecipe API
  const statResp = await fetch("/apps/figrecipe/figrecipe/stats/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ test_name: testName, groups }),
  });
  const { result, annotation } = await statResp.json();

  // Forward stat bracket to figrecipe renderer
  const bracketResp = await fetch(
    "/apps/figrecipe/figrecipe/stats/add_bracket",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        annotation,
        ax_index: axIndex,
        group_positions: groupPositions,
      }),
    },
  );
  const { bracket_id, preview } = await bracketResp.json();

  console.log(
    `[Bridge] Stat → bracket: ${testName} → ${annotation.stars} (${bracket_id})`,
  );

  return { result, annotation, bracket_id, preview };
}
