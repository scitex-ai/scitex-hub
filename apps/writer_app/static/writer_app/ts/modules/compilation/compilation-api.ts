/**
 * Compilation API
 * Handles HTTP requests for compilation operations
 */

import { getCsrfToken } from "@/utils/csrf";
import { CompilationOptions, CompilationResult } from "./types.js";

export class CompilationAPI {
  /**
   * Call preview compilation API
   */
  async compilePreview(
    options: CompilationOptions,
    timeoutMs: number = 60000,
  ): Promise<CompilationResult> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      // Determine effective color mode
      let effectiveColorMode = options.colorMode || "light";
      if (!options.colorMode) {
        const savedPdfTheme = localStorage.getItem("pdf-color-mode");
        if (savedPdfTheme === "light" || savedPdfTheme === "dark") {
          effectiveColorMode = savedPdfTheme;
        } else {
          const globalTheme =
            document.documentElement.getAttribute("data-theme") || "light";
          effectiveColorMode = globalTheme === "dark" ? "dark" : "light";
        }
        console.log(
          "[CompilationAPI] Using effective color mode:",
          effectiveColorMode,
        );
      }

      const response = await fetch(
        `/writer/api/project/${options.projectId}/compile_preview/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            content: options.content,
            timeout: timeoutMs / 1000,
            color_mode: effectiveColorMode,
            section_name: options.sectionName || "preview",
          }),
          signal: controller.signal,
        },
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return (await response.json()) as CompilationResult;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /**
   * Call full compilation API
   */
  async compileFull(
    options: CompilationOptions,
    timeoutMs: number = 300000,
  ): Promise<CompilationResult> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      console.log("[CompilationAPI] Starting full compilation:", options.docType);

      const response = await fetch(
        `/writer/api/project/${options.projectId}/compile_full/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            doc_type: options.docType,
            timeout: timeoutMs / 1000,
            no_figs: options.noFigs || false,
            ppt2tif: options.ppt2tif || false,
            crop_tif: options.cropTif || false,
            quiet: options.quiet || false,
            verbose: options.verbose || false,
            force: options.force || false,
          }),
          signal: controller.signal,
        },
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return (await response.json()) as CompilationResult;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /**
   * Poll compilation status
   */
  async getStatus(
    projectId: number,
    jobId: string,
  ): Promise<CompilationResult> {
    const response = await fetch(
      `/writer/api/project/${projectId}/compilation/status/${jobId}/`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return (await response.json()) as CompilationResult;
  }

  /**
   * Cancel compilation job
   */
  async cancel(jobId: string): Promise<boolean> {
    try {
      const response = await fetch(`/writer/api/cancel-compilation/${jobId}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
      });

      if (!response.ok) {
        return false;
      }

      const result = await response.json();
      return result.success || false;
    } catch (error) {
      console.error("[CompilationAPI] Failed to cancel:", error);
      return false;
    }
  }

  /**
   * Check for existing PDF
   */
  async checkExistingPDF(
    projectSlug: string,
    docType: string = "manuscript",
  ): Promise<string | null> {
    try {
      const response = await fetch(
        `/writer/api/pdf/${projectSlug}/${docType}/`,
      );

      if (!response.ok) {
        return null;
      }

      const result = await response.json();
      if (result.success && result.data?.url) {
        return result.data.url;
      }

      return null;
    } catch (error) {
      console.error("[CompilationAPI] Failed to check existing PDF:", error);
      return null;
    }
  }
}
