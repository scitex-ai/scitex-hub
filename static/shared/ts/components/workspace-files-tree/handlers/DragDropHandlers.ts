/**
 * Drag and Drop Handlers for WorkspaceFilesTree
 * Handles file/folder drag and drop operations including external file uploads
 */

import type { TreeConfig } from '../types.js';

export class DragDropHandlers {
  private showMessage: (message: string, type: 'success' | 'error' | 'info') => void;

  constructor(
    private config: TreeConfig,
    private getCsrfToken: () => string,
    private refresh: () => Promise<void>,
    showMessage?: (message: string, type: 'success' | 'error' | 'info') => void
  ) {
    this.showMessage = showMessage || ((msg, type) => console.log(`[DragDrop] ${type}: ${msg}`));
  }

  attachDragDropListeners(container: HTMLElement): void {
    const treeEl = container.querySelector('.wft-tree');
    if (!treeEl) return;

    // Make the entire tree container a drop zone for external files
    this.attachContainerDropZone(container);

    // Make items draggable (internal drag)
    treeEl.addEventListener('dragstart', (e) => {
      const dragEvent = e as DragEvent;
      const target = dragEvent.target as HTMLElement;
      const item = target.closest('[data-path]');
      if (item && dragEvent.dataTransfer) {
        const path = item.getAttribute('data-path')!;
        dragEvent.dataTransfer.setData('text/plain', path);
        dragEvent.dataTransfer.setData('application/x-wft-internal', 'true');
        dragEvent.dataTransfer.effectAllowed = 'move';
        item.classList.add('wft-dragging');
      }
    });

    // Drag over folder (for internal moves)
    treeEl.addEventListener('dragover', (e) => {
      const dragEvent = e as DragEvent;
      dragEvent.preventDefault();
      const target = dragEvent.target as HTMLElement;
      const folderItem = target.closest('.wft-folder[data-path]');
      if (folderItem && dragEvent.dataTransfer) {
        dragEvent.dataTransfer.dropEffect = 'move';
        folderItem.classList.add('wft-drop-target');
      }
    });

    // Drag leave
    treeEl.addEventListener('dragleave', (e) => {
      const dragEvent = e as DragEvent;
      const target = dragEvent.target as HTMLElement;
      const folderItem = target.closest('.wft-folder[data-path]');
      if (folderItem) {
        folderItem.classList.remove('wft-drop-target');
      }
    });

    // Drop on folder (internal move or external file upload to specific folder)
    treeEl.addEventListener('drop', async (e) => {
      const dragEvent = e as DragEvent;
      dragEvent.preventDefault();
      dragEvent.stopPropagation();

      const target = dragEvent.target as HTMLElement;
      const folderItem = target.closest('.wft-folder[data-path]');

      if (dragEvent.dataTransfer) {
        // Check if this is an external file drop
        const files = dragEvent.dataTransfer.files;
        const isInternal = dragEvent.dataTransfer.types.includes('application/x-wft-internal');

        if (files.length > 0 && !isInternal) {
          // External file upload to specific folder
          const targetPath = folderItem?.getAttribute('data-path') || '';
          await this.uploadFiles(files, targetPath);
        } else if (folderItem && isInternal) {
          // Internal move (symlink creation)
          const sourcePath = dragEvent.dataTransfer.getData('text/plain');
          const targetPath = folderItem.getAttribute('data-path')!;

          if (sourcePath && targetPath && sourcePath !== targetPath) {
            await this.moveFile(sourcePath, targetPath);
          }
        }
      }

      // Clean up
      this.cleanupDragState(container);
    });

    // Drag end
    treeEl.addEventListener('dragend', () => {
      this.cleanupDragState(container);
    });
  }

  /** Attach drop zone to the entire container for external file uploads */
  private attachContainerDropZone(container: HTMLElement): void {
    let dragCounter = 0;

    // Prevent default drag behaviors on the whole container
    container.addEventListener('dragenter', (e) => {
      e.preventDefault();
      dragCounter++;
      const dragEvent = e as DragEvent;

      // Only show drop zone for external files
      if (dragEvent.dataTransfer?.types.includes('Files')) {
        container.classList.add('wft-drop-zone-active');
      }
    });

    container.addEventListener('dragover', (e) => {
      e.preventDefault();
      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer) {
        dragEvent.dataTransfer.dropEffect = 'copy';
      }
    });

    container.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dragCounter--;
      if (dragCounter === 0) {
        container.classList.remove('wft-drop-zone-active');
      }
    });

    container.addEventListener('drop', async (e) => {
      e.preventDefault();
      dragCounter = 0;
      container.classList.remove('wft-drop-zone-active');

      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer) {
        const files = dragEvent.dataTransfer.files;
        const isInternal = dragEvent.dataTransfer.types.includes('application/x-wft-internal');

        const target = dragEvent.target as HTMLElement;
        const folderEl = target.closest('.wft-folder[data-path]');
        const targetPath = folderEl?.getAttribute('data-path') || '';

        // Handle file drop
        if (files.length > 0 && !isInternal) {
          if (!folderEl) {
            await this.uploadFiles(files, '');
          }
          return;
        }

        // Handle URL drop (from web pages, MS Office, etc.)
        const droppedUrl = dragEvent.dataTransfer.getData('text/uri-list') ||
                           dragEvent.dataTransfer.getData('text/plain');
        if (droppedUrl && !isInternal && this.isDownloadableUrl(droppedUrl)) {
          await this.downloadAndUploadFromUrl(droppedUrl, targetPath);
        }
      }
    });
  }

  /** Clean up drag state classes */
  private cleanupDragState(container: HTMLElement): void {
    container.classList.remove('wft-drop-zone-active');
    document.querySelectorAll('.wft-dragging, .wft-drop-target').forEach(el => {
      el.classList.remove('wft-dragging');
      el.classList.remove('wft-drop-target');
    });
  }

  /** Upload files to the project */
  private async uploadFiles(files: FileList, targetPath: string): Promise<void> {
    const fileCount = files.length;
    this.showMessage(`Uploading ${fileCount} file${fileCount > 1 ? 's' : ''}...`, 'info');

    let successCount = 0;
    let errorCount = 0;

    for (const file of Array.from(files)) {
      try {
        await this.uploadFile(file, targetPath);
        successCount++;
      } catch (error) {
        console.error(`[DragDrop] Failed to upload ${file.name}:`, error);
        errorCount++;
      }
    }

    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Uploaded ${successCount} file${successCount > 1 ? 's' : ''}${errorCount > 0 ? ` (${errorCount} failed)` : ''}`,
        errorCount > 0 ? 'info' : 'success'
      );
    } else {
      this.showMessage(`Failed to upload files`, 'error');
    }
  }

  /** Upload a single file */
  private async uploadFile(file: File, targetPath: string): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', targetPath ? `${targetPath}/${file.name}` : file.name);

    const response = await fetch(`/${this.config.username}/${this.config.slug}/api/files/upload/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': this.getCsrfToken(),
      },
      body: formData,
    });

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Upload failed');
    }
  }

  /** Move file/folder to a new location (inside target folder) */
  private async moveFile(sourcePath: string, targetFolderPath: string): Promise<void> {
    try {
      const fileName = sourcePath.split('/').pop() || sourcePath;
      const destPath = targetFolderPath ? `${targetFolderPath}/${fileName}` : fileName;

      const response = await fetch(`/${this.config.username}/${this.config.slug}/api/files/move/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({ source_path: sourcePath, dest_path: destPath }),
      });

      const data = await response.json();
      if (data.success) {
        this.showMessage(`Moved to ${targetFolderPath || 'root'}`, 'success');
        await this.refresh();
      } else {
        this.showMessage(`Failed to move: ${data.error}`, 'error');
      }
    } catch (error) {
      this.showMessage('Failed to move file', 'error');
    }
  }

  /** Check if URL looks like a downloadable resource */
  private isDownloadableUrl(url: string): boolean {
    if (!url.startsWith('http://') && !url.startsWith('https://')) return false;
    // Accept any valid URL - the server will handle content type detection
    return true;
  }

  /** Download file from URL and upload to project */
  private async downloadAndUploadFromUrl(url: string, targetPath: string): Promise<void> {
    this.showMessage('Downloading...', 'info');

    try {
      // Extract filename from URL or generate one
      let fileName = url.split('/').pop()?.split('?')[0] || 'download';
      if (!fileName.includes('.')) {
        fileName += '.bin';
      }

      const response = await fetch(`/${this.config.username}/${this.config.slug}/api/files/upload-url/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({
          url: url,
          path: targetPath ? `${targetPath}/${fileName}` : fileName,
        }),
      });

      const data = await response.json();
      if (data.success) {
        this.showMessage(`Saved as ${data.path}`, 'success');
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, 'error');
      }
    } catch (error) {
      this.showMessage('Failed to download', 'error');
    }
  }

  private async createSymlink(sourcePath: string, targetPath: string): Promise<void> {
    try {
      const response = await fetch(`/${this.config.username}/${this.config.slug}/api/files/symlink/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({ source: sourcePath, target: targetPath }),
      });

      const data = await response.json();
      if (data.success) {
        this.showMessage('Symlink created', 'success');
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, 'error');
      }
    } catch (error) {
      this.showMessage('Failed to create symlink', 'error');
    }
  }
}
