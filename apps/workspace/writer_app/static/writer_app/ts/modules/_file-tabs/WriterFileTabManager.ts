/**
 * WriterFileTabManager
 * Manages file tabs for the /writer/ page, inspired by /code/ page implementation.
 * Shows open files as tabs with close buttons and active state.
 */

interface OpenFile {
  path: string;
  name: string;
  isModified: boolean;
}

export class WriterFileTabManager {
  private tabsContainer: HTMLElement | null = null;
  private openFiles: Map<string, OpenFile> = new Map();
  private currentFile: string | null = null;
  private onSwitchFile: ((path: string) => void) | null = null;
  private onCloseFile: ((path: string) => void) | null = null;
  private onNewFile: (() => void) | null = null;

  constructor() {
    this.tabsContainer = document.getElementById('file-tabs');
    this.setupEventListeners();
    console.log('[WriterFileTabManager] Initialized');
  }

  /**
   * Set callback functions for tab interactions
   */
  setCallbacks(
    onSwitch: (path: string) => void,
    onClose: (path: string) => void,
    onNew?: () => void
  ): void {
    this.onSwitchFile = onSwitch;
    this.onCloseFile = onClose;
    this.onNewFile = onNew || null;
  }

  /**
   * Open a file (add to tabs if not already open)
   */
  openFile(path: string, name?: string): void {
    if (!this.openFiles.has(path)) {
      this.openFiles.set(path, {
        path,
        name: name || this.getFileName(path),
        isModified: false
      });
    }
    this.setCurrentFile(path);
    this.renderTabs();
  }

  /**
   * Close a file tab
   */
  closeFile(path: string): void {
    if (!this.openFiles.has(path)) return;

    this.openFiles.delete(path);

    // If closing current file, switch to another tab
    if (this.currentFile === path) {
      const remaining = Array.from(this.openFiles.keys());
      if (remaining.length > 0) {
        this.setCurrentFile(remaining[remaining.length - 1]);
        if (this.onSwitchFile) {
          this.onSwitchFile(this.currentFile!);
        }
      } else {
        this.currentFile = null;
      }
    }

    if (this.onCloseFile) {
      this.onCloseFile(path);
    }

    this.renderTabs();
  }

  /**
   * Set the current active file
   */
  setCurrentFile(path: string): void {
    this.currentFile = path;
    this.renderTabs();
  }

  /**
   * Get current file path
   */
  getCurrentFile(): string | null {
    return this.currentFile;
  }

  /**
   * Mark a file as modified
   */
  setFileModified(path: string, isModified: boolean): void {
    const file = this.openFiles.get(path);
    if (file) {
      file.isModified = isModified;
      this.renderTabs();
    }
  }

  /**
   * Check if a file is open
   */
  isFileOpen(path: string): boolean {
    return this.openFiles.has(path);
  }

  /**
   * Get all open files
   */
  getOpenFiles(): string[] {
    return Array.from(this.openFiles.keys());
  }

  /**
   * Render all tabs
   */
  private renderTabs(): void {
    if (!this.tabsContainer) return;

    // Clear existing tabs (except the plus button)
    const plusBtn = this.tabsContainer.querySelector('#btn-new-file-tab');
    this.tabsContainer.innerHTML = '';

    // Add file tabs
    this.openFiles.forEach((file, path) => {
      const tab = this.createTabElement(file);
      this.tabsContainer!.appendChild(tab);
    });

    // Re-add plus button at the end
    if (plusBtn) {
      this.tabsContainer.appendChild(plusBtn);
    } else {
      const newPlusBtn = document.createElement('button');
      newPlusBtn.id = 'btn-new-file-tab';
      newPlusBtn.className = 'file-tabs-plus-btn';
      newPlusBtn.title = 'New file';
      newPlusBtn.textContent = '+';
      newPlusBtn.addEventListener('click', () => {
        if (this.onNewFile) this.onNewFile();
      });
      this.tabsContainer.appendChild(newPlusBtn);
    }
  }

  /**
   * Create a tab element for a file
   */
  private createTabElement(file: OpenFile): HTMLElement {
    const tab = document.createElement('button');
    tab.className = 'file-tab';
    tab.dataset.filePath = file.path;
    tab.draggable = true;

    if (file.path === this.currentFile) {
      tab.classList.add('active');
    }
    if (file.isModified) {
      tab.classList.add('modified');
    }

    // File icon
    const icon = document.createElement('span');
    icon.className = 'file-tab-icon';
    icon.innerHTML = this.getFileIcon(file.name);
    tab.appendChild(icon);

    // File name
    const name = document.createElement('span');
    name.className = 'file-tab-name';
    name.textContent = file.name;
    tab.appendChild(name);

    // Close button
    const close = document.createElement('span');
    close.className = 'file-tab-close';
    close.textContent = '×';
    close.addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeFile(file.path);
    });
    tab.appendChild(close);

    // Click to switch
    tab.addEventListener('click', () => {
      if (this.currentFile !== file.path) {
        this.setCurrentFile(file.path);
        if (this.onSwitchFile) {
          this.onSwitchFile(file.path);
        }
      }
    });

    // Drag events
    tab.addEventListener('dragstart', (e) => {
      tab.classList.add('dragging');
      e.dataTransfer?.setData('text/plain', file.path);
    });

    tab.addEventListener('dragend', () => {
      tab.classList.remove('dragging');
    });

    tab.addEventListener('dragover', (e) => {
      e.preventDefault();
      tab.classList.add('drag-over');
    });

    tab.addEventListener('dragleave', () => {
      tab.classList.remove('drag-over');
    });

    tab.addEventListener('drop', (e) => {
      e.preventDefault();
      tab.classList.remove('drag-over');
      const draggedPath = e.dataTransfer?.getData('text/plain');
      if (draggedPath && draggedPath !== file.path) {
        this.reorderTabs(draggedPath, file.path);
      }
    });

    return tab;
  }

  /**
   * Reorder tabs (drag and drop)
   */
  private reorderTabs(draggedPath: string, targetPath: string): void {
    const entries = Array.from(this.openFiles.entries());
    const draggedIndex = entries.findIndex(([p]) => p === draggedPath);
    const targetIndex = entries.findIndex(([p]) => p === targetPath);

    if (draggedIndex === -1 || targetIndex === -1) return;

    // Remove dragged and insert at target position
    const [dragged] = entries.splice(draggedIndex, 1);
    entries.splice(targetIndex, 0, dragged);

    // Rebuild the map
    this.openFiles = new Map(entries);
    this.renderTabs();
  }

  /**
   * Get file name from path
   */
  private getFileName(path: string): string {
    return path.split('/').pop() || path;
  }

  /**
   * Get file icon based on extension
   */
  private getFileIcon(name: string): string {
    const ext = name.split('.').pop()?.toLowerCase() || '';
    const icons: { [key: string]: string } = {
      'tex': '<i class="fas fa-file-code"></i>',
      'bib': '<i class="fas fa-book"></i>',
      'pdf': '<i class="fas fa-file-pdf"></i>',
      'png': '<i class="fas fa-image"></i>',
      'jpg': '<i class="fas fa-image"></i>',
      'jpeg': '<i class="fas fa-image"></i>',
      'svg': '<i class="fas fa-image"></i>',
      'txt': '<i class="fas fa-file-alt"></i>',
      'md': '<i class="fab fa-markdown"></i>',
    };
    return icons[ext] || '<i class="fas fa-file"></i>';
  }

  /**
   * Setup global event listeners
   */
  private setupEventListeners(): void {
    // Plus button click
    const plusBtn = document.getElementById('btn-new-file-tab');
    if (plusBtn) {
      plusBtn.addEventListener('click', () => {
        if (this.onNewFile) this.onNewFile();
      });
    }

    // Keyboard shortcuts for tab navigation
    document.addEventListener('keydown', (e) => {
      // Ctrl+Tab or Ctrl+PageDown: Next tab
      if (e.ctrlKey && (e.key === 'Tab' || e.key === 'PageDown') && !e.shiftKey) {
        e.preventDefault();
        this.switchToNextTab();
      }
      // Ctrl+Shift+Tab or Ctrl+PageUp: Previous tab
      if (e.ctrlKey && ((e.key === 'Tab' && e.shiftKey) || e.key === 'PageUp')) {
        e.preventDefault();
        this.switchToPreviousTab();
      }
      // Ctrl+W: Close current tab
      if (e.ctrlKey && e.key === 'w') {
        e.preventDefault();
        if (this.currentFile) {
          this.closeFile(this.currentFile);
        }
      }
    });
  }

  /**
   * Switch to next tab
   */
  switchToNextTab(): void {
    const paths = Array.from(this.openFiles.keys());
    if (paths.length === 0 || !this.currentFile) return;

    const currentIndex = paths.indexOf(this.currentFile);
    const nextIndex = (currentIndex + 1) % paths.length;
    this.setCurrentFile(paths[nextIndex]);
    if (this.onSwitchFile) {
      this.onSwitchFile(paths[nextIndex]);
    }
  }

  /**
   * Switch to previous tab
   */
  switchToPreviousTab(): void {
    const paths = Array.from(this.openFiles.keys());
    if (paths.length === 0 || !this.currentFile) return;

    const currentIndex = paths.indexOf(this.currentFile);
    const prevIndex = (currentIndex - 1 + paths.length) % paths.length;
    this.setCurrentFile(paths[prevIndex]);
    if (this.onSwitchFile) {
      this.onSwitchFile(paths[prevIndex]);
    }
  }
}

// Export for global access
(window as any).WriterFileTabManager = WriterFileTabManager;
