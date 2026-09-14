/**
 * File Loader Module
 * Handles loading .tex files from the server
 */

import { showToast } from "../../utils/index";
import { getWriterConfig } from "../../_helpers";
import {
  fetchManuscriptStatus,
  ManuscriptStatusFetcher,
} from "./ManuscriptStatus";

export interface FileLoaderDependencies {
  getManuscriptStatus: ManuscriptStatusFetcher;
  fetchFile: typeof fetch;
}

const defaultDependencies: FileLoaderDependencies = {
  getManuscriptStatus: fetchManuscriptStatus,
  fetchFile: (...args) => fetch(...args),
};

async function manuscriptExists(
  projectId: number | string,
  getManuscriptStatus: ManuscriptStatusFetcher,
): Promise<boolean> {
  try {
    return (await getManuscriptStatus(projectId)).exists;
  } catch (error) {
    // Status unknown: fall back to the plain load rather than hiding a real manuscript.
    console.warn("[FileLoader] Manuscript status unavailable:", error);
    return true;
  }
}

/**
 * Load .tex file content from server
 */
export async function loadTexFile(
  filePath: string,
  editor: any,
  dependencies: FileLoaderDependencies = defaultDependencies,
): Promise<void> {
  console.log("[FileLoader] Loading .tex file:", filePath);

  const config = getWriterConfig();
  if (!config.projectId) {
    console.error("[FileLoader] Cannot load file: no project ID");
    showToast("Cannot load file: no project selected", "error");
    return;
  }

  if (
    !(await manuscriptExists(
      config.projectId,
      dependencies.getManuscriptStatus,
    ))
  ) {
    console.log("[FileLoader] No manuscript yet, skipping load:", filePath);
    return;
  }

  try {
    const response = await dependencies.fetchFile(
      `/apps/writer/api/project/${config.projectId}/read-tex-file/?path=${encodeURIComponent(filePath)}`,
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

    if (data.success && data.exists === false) {
      console.log("[FileLoader] File does not exist yet:", filePath);
      return;
    }

    console.log(
      "[FileLoader] File loaded successfully, length:",
      data.content?.length || 0,
    );

    if (data.success && data.content !== undefined) {
      editor.setContent(data.content);
      console.log("[FileLoader] File content set in editor");
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
