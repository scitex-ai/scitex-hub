/**
 * Run Manager
 * Handles file execution (Python, Shell, JS) via PTY terminal
 */

import type { EditorConfig } from "../core/types.js";
import type { PTYTerminal } from "../../pty-terminal.js";

export class RunManager {
  constructor(private config: EditorConfig) {}

  /**
   * Run a file based on its extension
   */
  async runFile(
    filePath: string,
    terminal: PTYTerminal,
    saveCallback: () => Promise<void>
  ): Promise<void> {
    if (!filePath) {
      console.warn("[RunManager] No file to run");
      return;
    }

    const ext = filePath.substring(filePath.lastIndexOf("."));

    switch (ext) {
      case ".py":
        await saveCallback();
        terminal.executeCommand(`python ${filePath}`);
        console.log(`[RunManager] Running: python ${filePath}`);
        break;
      case ".sh":
        await saveCallback();
        terminal.executeCommand(`bash ${filePath}`);
        console.log(`[RunManager] Running: bash ${filePath}`);
        break;
      case ".js":
        await saveCallback();
        terminal.executeCommand(`node ${filePath}`);
        console.log(`[RunManager] Running: node ${filePath}`);
        break;
      default:
        alert(`Cannot run ${ext} files. Only Python (.py), Shell (.sh), and JavaScript (.js) are supported.`);
    }
  }

  /**
   * Run scratch buffer by saving to temp file first
   * Uses /code/api/create-file/ and /code/api/save/ endpoints
   */
  async runScratchBuffer(
    content: string,
    terminal: PTYTerminal
  ): Promise<void> {
    if (!this.config.currentProject) {
      alert("No project selected");
      return;
    }

    const tempFileName = ".scratch_temp.py";
    console.log("[RunManager] Saving scratch buffer to", tempFileName);

    try {
      // First try to create the file
      let response = await fetch(`/code/api/create-file/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          project_id: this.config.currentProject.id,
          path: tempFileName,
          content: content,
        }),
      });

      // If create fails (file already exists), try save instead
      if (!response.ok) {
        console.log("[RunManager] Create failed, trying save...");
        response = await fetch(`/code/api/save/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.config.csrfToken,
          },
          body: JSON.stringify({
            project_id: this.config.currentProject.id,
            path: tempFileName,
            content: content,
          }),
        });
      }

      const data = await response.json();

      if (data.success || response.ok) {
        terminal.executeCommand(`python ${tempFileName}`);
        console.log("[RunManager] Running scratch buffer as", tempFileName);
      } else {
        console.error("[RunManager] Failed to save scratch:", data);
        alert("Failed to save scratch buffer: " + (data.error || data.message || "Unknown error"));
      }
    } catch (err) {
      console.error("[RunManager] Error saving scratch buffer:", err);
      alert("Failed to save scratch buffer for execution");
    }
  }
}
