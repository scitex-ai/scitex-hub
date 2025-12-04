/**
 * File Loader Module
 * Handles loading .tex files from the server
 */

import { showToast } from "../../utils/index.js";
import { getWriterConfig } from "../../helpers.js";

/**
 * Load .tex file content from server
 */
export async function loadTexFile(
  filePath: string,
  editor: any,
): Promise<void> {
  console.log("[FileLoader] Loading .tex file:", filePath);

  const config = getWriterConfig();
  if (!config.projectId) {
    console.error("[FileLoader] Cannot load file: no project ID");
    showToast("Cannot load file: no project selected", "error");
    return;
  }

  try {
    const response = await fetch(
      `/writer/api/project/${config.projectId}/read-tex-file/?path=${encodeURIComponent(filePath)}`,
    );

    console.log("[FileLoader] File API response status:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[FileLoader] Failed to load file:",
        response.status,
        errorText,
      );
      showToast(`Failed to load file: ${response.statusText}`, "error");
      return;
    }

    const data = await response.json();
    console.log(
      "[FileLoader] File loaded successfully, length:",
      data.content?.length || 0,
    );

    if (data.success && data.content !== undefined) {
      editor.setContent(data.content);
      console.log("[FileLoader] File content set in editor");
      showToast(`Loaded: ${filePath}`, "success");

      // Dispatch event to trigger PDF preview compilation
      window.dispatchEvent(
        new CustomEvent("writer:fileContentLoaded", {
          detail: { path: filePath, content: data.content },
        }),
      );
    } else {
      console.error("[FileLoader] Invalid response format:", data);
      showToast("Failed to load file: invalid response", "error");
    }
  } catch (error) {
    console.error("[FileLoader] Error loading file:", error);
    showToast(
      "Error loading file: " +
        (error instanceof Error ? error.message : "Unknown error"),
      "error",
    );
  }
}
