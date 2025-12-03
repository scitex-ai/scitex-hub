/**
 * Event Handlers for WorkspaceFilesTree
 * Handles file/folder click events
 */

import type { TreeItem, TreeConfig } from '../types.js';
import type { TreeStateManager } from '../TreeState.js';

export class EventHandlers {
  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private onToggleFolder: (path: string) => void,
    private onSelectFile: (path: string, event?: MouseEvent) => void,
    private onRename: (path: string, el: HTMLElement) => void,
    private onDelete?: (path: string) => void,
    private onNewFile?: (folderPath: string) => void,
    private onNewFolder?: (folderPath: string) => void,
    private onCopy?: (path: string) => void,
    private onGitAction?: (action: string, path: string) => void
  ) {}

  attachEventListeners(container: HTMLElement): void {
    const treeEl = container.querySelector('.wft-tree');
    if (!treeEl) return;

    // Git panel button clicks
    const gitPanel = container.querySelector('.wft-git-panel');
    if (gitPanel) {
      gitPanel.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        const btn = target.closest('[data-action]') as HTMLElement;
        if (btn && this.onGitAction) {
          e.preventDefault();
          e.stopPropagation();
          const action = btn.getAttribute('data-action');
          if (action) {
            this.onGitAction(action, '');
          }
        }
      });
    }

    // File/folder click (ignore right-clicks - context menu handles those)
    treeEl.addEventListener('click', (evt) => {
      const e = evt as MouseEvent;
      // Ignore right-click - context menu handles it
      if (e.button !== 0) return;
      const target = e.target as HTMLElement;

      // Action buttons (delete, new-file, new-folder)
      const actionBtn = target.closest('.wft-action-btn') as HTMLElement;
      if (actionBtn) {
        e.preventDefault();
        e.stopPropagation();
        const action = actionBtn.getAttribute('data-action');
        const path = actionBtn.getAttribute('data-path');

        if (action === 'delete' && path && this.onDelete) {
          this.onDelete(path);
        } else if (action === 'new-file' && path && this.onNewFile) {
          this.onNewFile(path);
        } else if (action === 'new-folder' && path && this.onNewFolder) {
          this.onNewFolder(path);
        } else if (action === 'rename' && path) {
          const item = actionBtn.closest('[data-path]') as HTMLElement;
          if (item) {
            this.onRename(path, item);
          }
        } else if (action === 'copy' && path && this.onCopy) {
          this.onCopy(path);
        } else if (action?.startsWith('git-') && path && this.onGitAction) {
          // Git actions: git-stage, git-unstage, git-discard, git-history, git-diff
          this.onGitAction(action, path);
        }
        return;
      }

      // Folder toggle (chevron icon)
      const chevron = target.closest('.wft-folder-chevron');
      if (chevron) {
        e.preventDefault();
        const folderItem = chevron.closest('[data-path]');
        if (folderItem) {
          const path = folderItem.getAttribute('data-path')!;
          this.onToggleFolder(path);
        }
        return;
      }

      // File selection
      const fileItem = target.closest('.wft-file[data-path]');
      if (fileItem && !fileItem.classList.contains('disabled')) {
        e.preventDefault();
        const path = fileItem.getAttribute('data-path')!;
        this.onSelectFile(path, e);
        return;
      }

      // Folder selection (click anywhere on folder row)
      const folderItem = target.closest('.wft-folder[data-path]');
      if (folderItem && !folderItem.classList.contains('disabled')) {
        // Toggle folder when clicking anywhere on the folder row
        // Exclude clicks on action buttons
        const clickedOnAction = target.closest('.wft-action-btn');

        if (!clickedOnAction) {
          e.preventDefault();
          const path = folderItem.getAttribute('data-path')!;
          this.onToggleFolder(path);
        }
      }
    });

    // Double-click to rename
    treeEl.addEventListener('dblclick', (e) => {
      const target = e.target as HTMLElement;
      const item = target.closest('[data-path]');
      if (item) {
        e.preventDefault();
        const path = item.getAttribute('data-path')!;
        this.onRename(path, item as HTMLElement);
      }
    });

    // Context menu
    treeEl.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      // Context menu can be implemented here
    });
  }
}
