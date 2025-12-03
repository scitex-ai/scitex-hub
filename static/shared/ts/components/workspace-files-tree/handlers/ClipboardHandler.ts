/**
 * ClipboardHandler - Handles clipboard operations (cut, copy, paste)
 *
 * Works with both single and multi-selection
 */

import type { TreeConfig } from '../types.js';

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

  // Clipboard state (persisted in memory for now)
  private clipboard: ClipboardState | null = null;

  constructor(
    config: TreeConfig,
    getCsrfToken: () => string,
    refresh: () => Promise<void>,
    showMessage: (message: string, type: 'success' | 'error' | 'info') => void,
    getSelectedPaths: () => string[]
  ) {
    this.config = config;
    this.getCsrfToken = getCsrfToken;
    this.refresh = refresh;
    this.showMessage = showMessage;
    this.getSelectedPaths = getSelectedPaths;
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
    if (!this.clipboard) {
      this.showMessage('Nothing to paste', 'info');
      return false;
    }

    const { operation, paths } = this.clipboard;

    try {
      // Determine if target is a directory
      const isDirectory = await this.isDirectory(targetPath);
      const destDir = isDirectory ? targetPath : this.getParentPath(targetPath);

      let successCount = 0;
      let errors: string[] = [];

      for (const sourcePath of paths) {
        const fileName = this.getFileName(sourcePath);
        const destPath = destDir ? `${destDir}/${fileName}` : fileName;

        // Don't allow pasting into itself
        if (sourcePath === destPath || destPath.startsWith(sourcePath + '/')) {
          errors.push(`Cannot ${operation} '${fileName}' into itself`);
          continue;
        }

        try {
          if (operation === 'copy') {
            await this.performCopy(sourcePath, destPath);
          } else {
            await this.performMove(sourcePath, destPath);
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
          `${verb} ${successCount} item${successCount > 1 ? 's' : ''}`,
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

  /** Perform copy operation */
  private async performCopy(sourcePath: string, destPath: string): Promise<void> {
    const response = await fetch(this.getApiUrl('copy'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken(),
      },
      body: JSON.stringify({ source_path: sourcePath, dest_path: destPath }),
    });

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Copy failed');
    }
  }

  /** Perform move operation */
  private async performMove(sourcePath: string, destPath: string): Promise<void> {
    const response = await fetch(this.getApiUrl('move'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken(),
      },
      body: JSON.stringify({ source_path: sourcePath, dest_path: destPath }),
    });

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Move failed');
    }
  }

  /** Check if path is a directory */
  private async isDirectory(path: string): Promise<boolean> {
    // For now, assume paths without extensions are directories
    // A more robust approach would be to check the actual tree data
    return !path.includes('.') || path.endsWith('/');
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
    document.querySelectorAll('.wft-item.wft-cut, .wft-item.wft-copied').forEach(el => {
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
    }
  }

  /** Re-apply visual classes after tree re-render */
  reapplyClasses(): void {
    this.updateCutCopyClasses();
  }
}
