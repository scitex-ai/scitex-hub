/**
 * Scratch Manager
 * Handles scratch buffer initialization and content generation
 */

import type { EditorConfig } from "../core/types.js";
import type { MonacoManager } from "./MonacoManager.js";
import type { FileStateManager } from "../files/FileStateManager.js";

export class ScratchManager {
  constructor(
    private config: EditorConfig,
    private monacoManager: MonacoManager
  ) {}

  /**
   * Initialize scratch buffer with default content
   */
  async initialize(fileStateManager: FileStateManager): Promise<void> {
    console.log("[ScratchManager] Initializing scratch buffer...");

    await this.monacoManager.initialize("python");

    const editor = this.monacoManager.getEditor();
    if (!editor) {
      console.error("[ScratchManager] Editor not available after initialization");
      return;
    }

    // Show monaco editor, hide media preview
    const monacoEditor = document.getElementById("monaco-editor");
    const mediaPreview = document.getElementById("media-preview");
    if (monacoEditor) monacoEditor.style.display = "block";
    if (mediaPreview) mediaPreview.style.display = "none";

    // Get default scratch content
    const scratchContent = this.getContent();
    editor.setValue(scratchContent);

    // Initialize scratch buffer in file state manager
    fileStateManager.initializeScratchBuffer(scratchContent);

    const toolbarFilePath = document.getElementById("toolbar-file-path");
    if (toolbarFilePath) {
      toolbarFilePath.textContent = "*scratch*";
    }

    // Enable Run button for scratch
    const btnRun = document.getElementById("btn-run") as HTMLButtonElement;
    if (btnRun) {
      btnRun.disabled = false;
      btnRun.title = "Run: python .scratch_temp.py (Ctrl+Enter)";
    }

    console.log("[ScratchManager] Scratch buffer initialized");
  }

  /**
   * Generate scratch buffer content with project info
   */
  getContent(): string {
    const username = this.config.currentProject?.owner || "username";
    const projectName = this.config.currentProject?.name || "your-project";
    const projectSlug = this.config.currentProject?.slug || "your-project";

    const host = window.location.host;
    const protocol = window.location.protocol;
    const workspaceUrl = `${protocol}//${host}/code/`;
    const projectUrl = `${protocol}//${host}/${username}/${projectSlug}/`;
    const sshKeysUrl = `${protocol}//${host}/accounts/settings/ssh-keys/`;

    const isDev = host.includes("127.0.0.1") || host.includes("localhost");
    const sshHost = isDev ? "127.0.0.1" : "scitex.cloud";
    const sshPort = isDev ? "2200" : "2200";

    return `#!/usr/bin/env python3
# SciTeX Code Workspace
#
# Project: ${projectName}
# User:    ${username}
#
# URLs:
#   Workspace:  ${workspaceUrl}
#   Project:    ${projectUrl}
#   SSH Keys:   ${sshKeysUrl}
#
# SSH Access:
#   1. Add SSH key: ${sshKeysUrl}
#   2. Connect:     ssh -p ${sshPort} ${username}@${sshHost}
#
# Keyboard Shortcuts:
#   Ctrl+S         Save file
#   Ctrl+Enter     Run Python file
#   Keyboard btn   Show all shortcuts
#   Ctrl+Shift+R   Reset this buffer
#
# Editor Mode: Emacs | Vim | VS Code (toolbar dropdown)

def hello():
    """Example function"""
    print("Hello from SciTeX!")
    print(f"Project: ${projectName}")
    print(f"User: ${username}")
    print(f"SSH: ssh -p ${sshPort} ${username}@${sshHost}")

if __name__ == "__main__":
    hello()
    `;
  }
}
