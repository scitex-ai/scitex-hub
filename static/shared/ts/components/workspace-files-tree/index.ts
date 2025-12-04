/**
 * Workspace Files Tree - Main Export
 * Unified file tree component for all workspace modules
 *
 * Usage:
 * ```typescript
 * import { WorkspaceFilesTree } from '@shared/components/workspace-files-tree';
 *
 * const tree = new WorkspaceFilesTree({
 *   mode: 'code',
 *   containerId: 'file-tree',
 *   username: 'test-user',
 *   slug: 'my-project',
 *   onFileSelect: (path, item) => {
 *     console.log('Selected:', path);
 *   },
 * });
 *
 * await tree.initialize();
 * ```
 */

export { WorkspaceFilesTree } from './WorkspaceFilesTree.ts';
export { TreeStateManager } from './TreeState.ts';
export { TreeFilter } from './TreeFilter.ts';
export { TreeRenderer } from './TreeRenderer.ts';
export type {
  TreeItem,
  TreeConfig,
  TreeState,
  FilterConfig,
  WorkspaceMode,
} from './types.ts';
export { MODE_FILTERS } from './types.ts';
