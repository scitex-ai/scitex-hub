/**
 * ClipboardHandler - Handles clipboard operations (cut, copy, paste)
 *
 * Works with both single and multi-selection
 */

import type { TreeConfig } from '../types.ts';
import type { FileOperation } from './UndoRedoHandler.ts';

export type ClipboardOperation = 'cut' | 'copy';

export interface ClipboardState {
  operation: ClipboardOperation;
  paths: string[];
  timestamp: number;
}

export class ClipboardHandler {
  private config: TreeConfig;
  private getCsrfToken: () => string;
  private refresh: () => Promise<void>;
  private showMessage: (message: string, type: 'success' | 'error' | 'info') => void;
  private getSelectedPaths: () => string[];
  private isPathDirectory: (path: string) => boolean;
  private recordOperation: ((op: FileOperation) => void) | null = null;

  // Clipboard state (persisted in memory for now)
  private clipboard: ClipboardState | null = null;

  constructor(
    config: TreeConfig,
    getCsrfToken: () => string,
    refresh: () => Promise<void>,
    showMessage: (message: string, type: 'success' | 'error' | 'info') => void,
    getSelectedPaths: () => string[],
    isPathDirectory: (path: string) => boolean
  ) {
    this.config = config;
    this.getCsrfToken = getCsrfToken;
    this.refresh = refresh;
    this.showMessage = showMessage;
    this.getSelectedPaths = getSelectedPaths;
    this.isPathDirectory = isPathDirectory;
  }

  /** Set callback to record operations for undo/redo */
  setRecordOperation(callback: (op: FileOperation) => void): void {
    this.recordOperation = callback;
  }

  /** Get the base API URL for file operations */
  private getApiUrl(action: string): string {
    return `/${this.config.username}/${this.config.slug}/api/files/${action}/`;
  }

  /** Copy selected files to clipboard (internal + OS clipboard) */
  copy(paths?: string[]): void {
    const pathsToCopy = paths || this.getSelectedPaths();
    if (pathsToCopy.length === 0) {
      this.showMessage('No files selected', 'info');
      return;
    }

    this.clipboard = {
      operation: 'copy',
      paths: pathsToCopy,
      timestamp: Date.now(),
    };

    // Also copy to OS clipboard for external paste
    this.copyToOsClipboard(pathsToCopy);

    this.showMessage(
      pathsToCopy.length === 1
        ? `Copied: ${this.getFileName(pathsToCopy[0])}`
        : `Copied ${pathsToCopy.length} items`,
      'success'
    );

    // Add visual feedback
    this.updateCutCopyClasses();
  }

  /** Copy file content to OS clipboard for pasting in file explorers */
  private async copyToOsClipboard(paths: string[]): Promise<void> {
    if (paths.length !== 1) {
      // Multi-file copy to OS not supported, just copy paths as text
      try {
        await navigator.clipboard.writeText(paths.join('\n'));
      } catch (e) {
        // Ignore clipboard errors
      }
      return;
    }

    const filePath = paths[0];
    const fileName = this.getFileName(filePath);

    try {
      // Fetch file content as blob
      const url = `/${this.config.username}/${this.config.slug}/blob/${filePath}?mode=raw`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch file');
      }

      const blob = await response.blob();
      const contentType = blob.type || 'application/octet-stream';

      // Try to copy as file using ClipboardItem API
      if ('ClipboardItem' in window) {
        try {
          const clipboardItem = new ClipboardItem({
            [contentType]: blob,
          });
          await navigator.clipboard.write([clipboardItem]);
          return;
        } catch (e) {
          // ClipboardItem may not support this content type
        }
      }

      // Fallback: for text files, copy as text
      if (contentType.startsWith('text/') || fileName.match(/\.(txt|md|json|js|ts|py|html|css|xml|yaml|yml)$/i)) {
        const text = await blob.text();
        await navigator.clipboard.writeText(text);
      } else {
        // For binary files, just copy the path
        await navigator.clipboard.writeText(filePath);
      }
    } catch (e) {
      // Silently fail - internal clipboard still works
    }
  }

  /** Cut selected files (mark for move) */
  cut(paths?: string[]): void {
    const pathsToCut = paths || this.getSelectedPaths();
    if (pathsToCut.length === 0) {
      this.showMessage('No files selected', 'info');
      return;
    }

    this.clipboard = {
      operation: 'cut',
      paths: pathsToCut,
      timestamp: Date.now(),
    };

    this.showMessage(
      pathsToCut.length === 1
        ? `Cut: ${this.getFileName(pathsToCut[0])}`
        : `Cut ${pathsToCut.length} items`,
      'success'
    );

    // Add visual feedback for cut items
    this.updateCutCopyClasses();
  }

  /** Paste clipboard contents to target directory */
  async paste(targetPath: string): Promise<boolean> {
    console.log('[ClipboardHandler] paste() called with targetPath:', JSON.stringify(targetPath));

    if (!this.clipboard) {
      this.showMessage('Nothing to paste', 'info');
      return false;
    }

    const { operation, paths } = this.clipboard;
    console.log('[ClipboardHandler] operation:', operation, 'paths:', paths);

    try {
      // Determine if target is a directory
      const isDirectory = await this.isDirectory(targetPath);
      const destDir = isDirectory ? targetPath : this.getParentPath(targetPath);
      console.log('[ClipboardHandler] isDirectory:', isDirectory, 'destDir:', JSON.stringify(destDir));

      let successCount = 0;
      let errors: string[] = [];

      for (const sourcePath of paths) {
        const fileName = this.getFileName(sourcePath);
        let destPath = destDir ? `${destDir}/${fileName}` : fileName;
        console.log('[ClipboardHandler] sourcePath:', sourcePath, 'destPath:', destPath);

        // For copy: if source equals destination, start with suffix
        // For cut/move: can't move to same location
        if (sourcePath === destPath) {
          if (operation === 'copy') {
            // Start with suffix (1) for same-location copy
            destPath = this.getPathWithSuffix(destPath, 1);
          } else {
            // Can't move to same location
            errors.push(`Cannot move '${fileName}' to same location`);
            continue;
          }
        }

        // Don't allow pasting into a subdirectory of itself
        if (destPath.startsWith(sourcePath + '/')) {
          errors.push(`Cannot ${operation} '${fileName}' into itself`);
          continue;
        }

        try {
          let finalDestPath: string;
          const isDir = this.isPathDirectory(sourcePath);
          if (operation === 'copy') {
            finalDestPath = await this.performCopy(sourcePath, destPath);
            // Record for undo
            if (this.recordOperation) {
              this.recordOperation({
                type: 'copy',
                timestamp: Date.now(),
                originalPath: sourcePath,
                newPath: finalDestPath,
                isDirectory: isDir,
              });
            }
          } else {
            finalDestPath = await this.performMove(sourcePath, destPath);
            // Record for undo (move is like rename)
            if (this.recordOperation) {
              this.recordOperation({
                type: 'move',
                timestamp: Date.now(),
                originalPath: sourcePath,
                newPath: finalDestPath,
                isDirectory: isDir,
              });
            }
          }
          successCount++;
        } catch (error: any) {
          errors.push(`${fileName}: ${error.message || 'Unknown error'}`);
        }
      }

      // Clear clipboard after cut (not after copy)
      if (operation === 'cut' && successCount > 0) {
        this.clipboard = null;
        this.updateCutCopyClasses();
      }

      // Refresh the tree
      await this.refresh();

      // Show result
      if (successCount > 0) {
        const verb = operation === 'cut' ? 'Moved' : 'Copied';
        this.showMessage(
          `${verb} ${successCount} item${successCount > 1 ? 's' : ''} (Ctrl+Z to undo)`,
          'success'
        );
      }

      if (errors.length > 0) {
        this.showMessage(`Errors: ${errors.join(', ')}`, 'error');
      }

      return successCount > 0;
    } catch (error) {
      console.error('[ClipboardHandler] Paste error:', error);
      this.showMessage('Failed to paste items', 'error');
      return false;
    }
  }

  /** Check if there's anything in the clipboard */
  hasClipboard(): boolean {
    return this.clipboard !== null && this.clipboard.paths.length > 0;
  }

  /** Get clipboard operation type */
  getClipboardOperation(): ClipboardOperation | null {
    return this.clipboard?.operation ?? null;
  }

  /** Get clipboard paths */
  getClipboardPaths(): string[] {
    return this.clipboard?.paths ?? [];
  }

  /** Clear clipboard */
  clearClipboard(): void {
    this.clipboard = null;
    this.updateCutCopyClasses();
  }

  /** Perform copy operation with automatic suffix on conflict. Returns actual dest path. */
  private async performCopy(sourcePath: string, destPath: string): Promise<string> {
    let finalDestPath = destPath;
    let attempt = 0;
    const maxAttempts = 100;

    while (attempt < maxAttempts) {
      const response = await fetch(this.getApiUrl('copy'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({ source_path: sourcePath, dest_path: finalDestPath }),
      });

      const data = await response.json();
      if (data.success) {
        return finalDestPath;
      }

      // If destination exists, try with suffix
      if (data.error && data.error.includes('already exists')) {
        attempt++;
        finalDestPath = this.getPathWithSuffix(destPath, attempt);
        continue;
      }

      throw new Error(data.error || 'Copy failed');
    }

    throw new Error('Too many files with similar names');
  }

  /** Perform move operation with automatic suffix on conflict. Returns actual dest path. */
  private async performMove(sourcePath: string, destPath: string): Promise<string> {
    let finalDestPath = destPath;
    let attempt = 0;
    const maxAttempts = 100;

    while (attempt < maxAttempts) {
      const response = await fetch(this.getApiUrl('move'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({ source_path: sourcePath, dest_path: finalDestPath }),
      });

      const data = await response.json();
      if (data.success) {
        return finalDestPath;
      }

      // If destination exists, try with suffix
      if (data.error && data.error.includes('already exists')) {
        attempt++;
        finalDestPath = this.getPathWithSuffix(destPath, attempt);
        continue;
      }

      throw new Error(data.error || 'Move failed');
    }

    throw new Error('Too many files with similar names');
  }

  /** Get path with numbered suffix: file.txt -> file (1).txt */
  private getPathWithSuffix(path: string, suffix: number): string {
    const parts = path.split('/');
    const fileName = parts.pop() || path;
    const parentPath = parts.join('/');

    // Handle extension
    const dotIndex = fileName.lastIndexOf('.');
    let newName: string;
    if (dotIndex > 0) {
      const baseName = fileName.substring(0, dotIndex);
      const ext = fileName.substring(dotIndex);
      newName = `${baseName} (${suffix})${ext}`;
    } else {
      newName = `${fileName} (${suffix})`;
    }

    return parentPath ? `${parentPath}/${newName}` : newName;
  }

  /** Check if path is a directory using tree data */
  private async isDirectory(path: string): Promise<boolean> {
    // Empty path is root directory
    if (path === '') return true;
    // Use the provided function to check tree data
    return this.isPathDirectory(path);
  }

  /** Get parent path */
  private getParentPath(path: string): string {
    const parts = path.split('/');
    parts.pop();
    return parts.join('/');
  }

  /** Get file name from path */
  private getFileName(path: string): string {
    return path.split('/').pop() || path;
  }

  /** Update visual classes for cut/copy items */
  private updateCutCopyClasses(): void {
    // Remove all existing cut/copy classes
    const cutItems = document.querySelectorAll('.wft-item.wft-cut, .wft-item.wft-copied');
    console.log('[ClipboardHandler] Removing cut/copy classes from', cutItems.length, 'items');
    cutItems.forEach(el => {
      el.classList.remove('wft-cut', 'wft-copied');
    });

    if (this.clipboard) {
      const className = this.clipboard.operation === 'cut' ? 'wft-cut' : 'wft-copied';
      for (const path of this.clipboard.paths) {
        const el = document.querySelector(`.wft-item[data-path="${path}"]`);
        if (el) {
          el.classList.add(className);
        }
      }
      console.log('[ClipboardHandler] Added', className, 'class to', this.clipboard.paths.length, 'items');
    } else {
      console.log('[ClipboardHandler] Clipboard cleared, no classes to add');
    }
  }

  /** Re-apply visual classes after tree re-render */
  reapplyClasses(): void {
    this.updateCutCopyClasses();
  }
}
