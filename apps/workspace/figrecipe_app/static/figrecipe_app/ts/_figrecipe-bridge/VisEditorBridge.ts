/**
 * VisEditorBridge — connects figrecipe bridge events to existing TS managers.
 *
 * Listens for CustomEvents emitted by the React bridge and calls
 * the appropriate VisEditor / manager methods.
 */

import { onBridgeEvent } from "./BridgeEventBus";
import { switchRecipeFile } from "./FigrecipeMountPoint";
import { runTest, forwardStatToFigrecipe } from "../_vis/StatsApiClient";
import type { GroupData } from "../_vis/StatsTypes";

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
 * Run a stat test via scitex.stats and render the bracket on figrecipe.
 *
 * End-to-end flow:
 *   1. POST /apps/figrecipe/api/stats/run/ → {result, annotation}
 *   2. POST /apps/figrecipe/api/figrecipe/stats/add_bracket → render bracket
 */
export async function runStatAndRenderBracket(
  testName: string,
  groups: GroupData[],
  axIndex: number = 0,
  groupPositions?: { x1: number; x2: number },
): Promise<{
  result: any;
  annotation: any;
  bracket_id: string;
  preview: string;
}> {
  const { result, annotation } = await runTest(testName, groups);
  const { bracket_id, preview } = await forwardStatToFigrecipe(
    annotation,
    axIndex,
    groupPositions,
  );

  console.log(
    `[Bridge] Stat → bracket: ${testName} → ${annotation.stars} (${bracket_id})`,
  );

  return { result, annotation, bracket_id, preview };
}
