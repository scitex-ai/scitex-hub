/**
 * Platform FrontendKit — Component registry for user apps.
 *
 * Re-exports existing shared components as the public API
 * that plugin developers use. Centralizes imports so plugins
 * don't need to know internal paths.
 *
 * Usage in a user app:
 *   import { DataTableManager, initMonacoEditor } from "platform/frontendkit";
 */

// ── Data Table ──────────────────────────────────────────
export { DataTableManager } from "../components/data-table/DataTableManager";

// ── Monaco Editor ───────────────────────────────────────
export { SharedMonacoEditor } from "../components/monaco-editor/SharedMonacoEditor";

// ── Media Viewer (PDF, images, video, audio, Mermaid) ───
export { WorkspaceViewer } from "../components/workspace-viewer/WorkspaceViewer";

// ── File Tree ───────────────────────────────────────────
export { WorkspaceFilesTree } from "../components/workspace-files-tree/WorkspaceFilesTree";

// ── File Tabs ───────────────────────────────────────────
export { FileTabBar } from "../components/file-tabs/FileTabBar";

// ── Resizer (split panes) ───────────────────────────────
export { HorizontalResizer } from "../components/resizer/HorizontalResizer";
export { VerticalResizer } from "../components/resizer/VerticalResizer";

// ── Component Registry ──────────────────────────────────
// Maps component names to their classes for dynamic instantiation.

export const COMPONENT_REGISTRY: Record<string, unknown> = {};

/**
 * Register a component for use by plugin apps.
 * Plugins can call `getComponent("MyComponent")` to access it.
 */
export function registerComponent(name: string, component: unknown): void {
  COMPONENT_REGISTRY[name] = component;
}

/**
 * Get a registered component by name.
 * Returns undefined if not found.
 */
export function getComponent(name: string): unknown {
  return COMPONENT_REGISTRY[name];
}

/**
 * List all registered component names.
 */
export function listComponents(): string[] {
  return Object.keys(COMPONENT_REGISTRY).sort();
}
