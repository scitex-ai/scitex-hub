/**
 * File State Manager
 * Manages open files, current file state, and file switching
 * Supports both text files (Monaco editor) and media files (MediaViewer)
 */

import type { OpenFile, FileType } from "../core/types.ts";
import { detectFileType } from "../core/types.ts";
import { MonacoManager } from "../editor/MonacoManager.ts";
import { MediaViewerManager } from "../editor/MediaViewerManager.ts";
import { FileOperations } from "./FileOperations.ts";
import { FileTabManager } from "./FileTabManager.ts";
import { GitStatusManager } from "../git/GitStatusManager.ts";

export class FileStateManager {
  private currentFile: string | null = null;
  private mediaViewerManager: MediaViewerManager;

  constructor(
    private monacoManager: MonacoManager,
    private fileOperations: FileOperations,
    private fileTabManager: FileTabManager,
    private gitStatusManager: GitStatusManager,
    private openFiles: Map<string, OpenFile> = new Map()
  ) {
    this.mediaViewerManager = new MediaViewerManager();
  }

  /**
   * Set the shared openFiles map (used when FileTabManager provides the map)
   */
  setOpenFilesMap(map: Map<string, OpenFile>): void {
    this.openFiles = map;
  }

  /**
   * Handle file click from file tree
   */
  handleFileClick(filePath: string): void {
    this.loadFile(filePath);
  }

  /**
   * Load a file from the server and open it
   */
  async loadFile(filePath: string): Promise<void> {
    console.log(`[FileStateManager] Loading file: ${filePath}`);

    // Check if already open
    if (this.openFiles.has(filePath)) {
      console.log(`[FileStateManager] File already open, switching to it`);
      this.switchToFile(filePath);
      return;
    }

    // Detect file type
    const fileType = detectFileType(filePath);
    console.log(`[FileStateManager] Detected file type: ${fileType}`);

    // For media files (image, pdf, csv), we don't need to load content into Monaco
    if (fileType !== 'text') {
      // Add to open files with media type
      this.openFiles.set(filePath, {
        path: filePath,
        content: '', // Media files don't store text content
        language: '',
        fileType: fileType,
      });

      // Switch to the file (this also saves tab state)
      await this.switchToFile(filePath);
      // Explicitly save tab state after opening new file
      this.fileTabManager.saveTabState();
      return;
    }

    // Load text file from server
    const result = await this.fileOperations.loadFile(filePath);
    if (!result.success) {
      console.error(`[FileStateManager] Failed to load file: ${filePath}`);
      return;
    }

    const language = this.monacoManager.detectLanguage(filePath, result.content);

    // Add to open files
    this.openFiles.set(filePath, {
      path: filePath,
      content: result.content,
      language: language,
      fileType: 'text',
    });

    // Switch to the file (this also saves tab state)
    await this.switchToFile(filePath);
    // Explicitly save tab state after opening new file
    this.fileTabManager.saveTabState();
  }

  /**
   * Switch to an already-open file
   */
  async switchToFile(filePath: string): Promise<void> {
    const fileData = this.openFiles.get(filePath);
    if (!fileData) return;

    const editor = this.monacoManager.getEditor();

    // Save current file content before switching (only for text files)
    if (this.currentFile && this.currentFile !== filePath && editor) {
      const currentData = this.openFiles.get(this.currentFile);
      if (currentData && currentData.fileType === 'text') {
        currentData.content = editor.getValue();
      }
    }

    // Switch to new file
    this.currentFile = filePath;

    // Re-detect file type (in case fileType was not set correctly before)
    const fileType = detectFileType(filePath);
    // Update the stored fileType if it was wrong
    if (fileData.fileType !== fileType) {
      console.log(`[FileStateManager] Correcting fileType: ${fileData.fileType} -> ${fileType}`);
      fileData.fileType = fileType;
    }

    console.log(`[FileStateManager] File type for ${filePath}: ${fileType}`);

    if (fileType !== 'text') {
      // Show media viewer, hide Monaco
      console.log(`[FileStateManager] Displaying ${fileType} file in media viewer`);
      this.mediaViewerManager.displayFile(filePath, fileType, fileData.blobUrl);

      // Disable save/run buttons for media files
      const btnSave = document.getElementById("btn-save") as HTMLButtonElement;
      const btnRun = document.getElementById("btn-run") as HTMLButtonElement;
      if (btnSave) btnSave.disabled = true;
      if (btnRun) btnRun.disabled = true;
    } else {
      // Hide media viewer, show Monaco
      this.mediaViewerManager.hide();

      if (editor) {
        editor.setValue(fileData.content);

        // Update Monaco language
        const monaco = (window as any).monaco;
        if (monaco) {
          const model = editor.getModel();
          if (model) {
            monaco.editor.setModelLanguage(model, fileData.language);
          }
        }
      }

      // Enable save/run buttons for text files
      const btnSave = document.getElementById("btn-save") as HTMLButtonElement;
      const btnRun = document.getElementById("btn-run") as HTMLButtonElement;
      if (btnSave) btnSave.disabled = false;
      // Run only for Python files
      if (btnRun) btnRun.disabled = !filePath.endsWith('.py');

      // Update git decorations (only for text files)
      if (editor) {
        await this.gitStatusManager.updateGitDecorations(filePath, editor);
      }
    }

    // Update UI
    const toolbarFilePath = document.getElementById("toolbar-file-path");
    if (toolbarFilePath) {
      toolbarFilePath.textContent = filePath;
    }

    // Enable/disable delete button based on file type
    const btnDelete = document.getElementById("btn-delete") as HTMLButtonElement;
    if (btnDelete) {
      // Disable for scratch buffer, enable for real files
      btnDelete.disabled = filePath === "*scratch*";
    }

    // Update tabs
    this.fileTabManager.setCurrentFile(filePath);

    console.log(`[FileStateManager] Switched to file: ${filePath} (${fileType})`);
  }

  /**
   * Close a file tab
   */
  closeTab(filePath: string): void {
    // Call fileTabManager.closeTab first - it checks openFiles.has() before proceeding
    // Since we share the same openFiles map, we must call this before deleting
    this.fileTabManager.closeTab(filePath);

    // openFiles is already deleted by fileTabManager.closeTab since they share the map
    // But ensure it's deleted in case closeTab returned early for any reason
    this.openFiles.delete(filePath);

    // If closing current file, clear current file state
    if (this.currentFile === filePath) {
      this.currentFile = null;

      // Disable delete button when no file is open
      const btnDelete = document.getElementById("btn-delete") as HTMLButtonElement;
      if (btnDelete) {
        btnDelete.disabled = true;
      }
    }
  }

  /**
   * Save the currently open file
   */
  async saveCurrentFile(): Promise<void> {
    if (!this.currentFile || this.currentFile === "*scratch*") {
      console.log("[FileStateManager] Cannot save scratch buffer");
      return;
    }

    const editor = this.monacoManager.getEditor();
    if (!editor) return;

    const content = editor.getValue();
    const success = await this.fileOperations.saveFile(this.currentFile, content);

    if (success) {
      // Update in-memory content
      const fileData = this.openFiles.get(this.currentFile);
      if (fileData) {
        fileData.content = content;
      }

      // Update git status and decorations
      await this.gitStatusManager.updateGitStatus();
      await this.gitStatusManager.updateGitDecorations(this.currentFile, editor);
    }
  }

  /**
   * Get the currently active file path
   */
  getCurrentFile(): string | null {
    return this.currentFile;
  }

  /**
   * Get the open files map
   */
  getOpenFiles(): Map<string, OpenFile> {
    return this.openFiles;
  }

  /**
   * Check if a file is currently open
   */
  isFileOpen(filePath: string): boolean {
    return this.openFiles.has(filePath);
  }

  /**
   * Initialize scratch buffer as the current file
   * Used during workspace initialization
   */
  initializeScratchBuffer(content: string): void {
    this.currentFile = "*scratch*";
    this.openFiles.set("*scratch*", {
      path: "*scratch*",
      content: content,
      language: "python",
      fileType: "text",
    });
    this.fileTabManager.setCurrentFile(this.currentFile);
    this.fileTabManager.updateTabs();
  }

  /**
   * Rename a file in the open files map
   * Used when a file is renamed on the server
   */
  renameOpenFile(oldPath: string, newPath: string): void {
    if (this.openFiles.has(oldPath)) {
      const fileData = this.openFiles.get(oldPath)!;
      this.openFiles.delete(oldPath);
      fileData.path = newPath;
      this.openFiles.set(newPath, fileData);
    }

    // Update current file if it was the renamed file
    if (this.currentFile === oldPath) {
      this.currentFile = newPath;
      this.fileTabManager.setCurrentFile(newPath);
    }
  }
}
