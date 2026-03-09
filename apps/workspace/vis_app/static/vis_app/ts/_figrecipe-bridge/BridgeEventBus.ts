/**
 * Typed CustomEvent system for figrecipe React ↔ scitex-cloud TS communication.
 *
 * Events flow bidirectionally:
 *   React (figrecipe store changes) → CustomEvent → TS managers
 *   TS managers (file tree clicks)  → CustomEvent → React (store updates)
 */

// ── Event type map ──────────────────────────────────────────────

export interface BridgeEventMap {
  /** React → TS: a file was selected in figrecipe's file tree */
  "figrecipe:fileSelect": { path: string };
  /** React → TS: a canvas element was clicked */
  "figrecipe:elementSelect": {
    elementId: string;
    bbox: { x: number; y: number; w: number; h: number } | null;
  };
  /** React → TS: a property was changed */
  "figrecipe:propertyChange": { key: string; value: unknown };
  /** React → TS: data was imported or changed */
  "figrecipe:dataChange": { columns: string[]; rowCount: number };
  /** React → TS: a stat bracket was added */
  "figrecipe:statBracketAdd": {
    bracket_id: string;
    ax_index: number;
    x1: number;
    x2: number;
    p_value: number;
    stars: string;
  };
  /** TS → React: switch to a different recipe file */
  "figrecipe:switchFile": { path: string };
}

export type BridgeEventName = keyof BridgeEventMap;

// ── Emit / Listen helpers ───────────────────────────────────────

const target = document;

export function emitBridgeEvent<K extends BridgeEventName>(
  name: K,
  detail: BridgeEventMap[K],
): void {
  target.dispatchEvent(new CustomEvent(name, { detail }));
}

export function onBridgeEvent<K extends BridgeEventName>(
  name: K,
  handler: (detail: BridgeEventMap[K]) => void,
): () => void {
  const listener = (e: Event) => handler((e as CustomEvent).detail);
  target.addEventListener(name, listener);
  return () => target.removeEventListener(name, listener);
}
