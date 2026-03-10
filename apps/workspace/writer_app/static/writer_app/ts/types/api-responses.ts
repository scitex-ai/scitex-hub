/**
 * API Response Types
 * TypeScript interfaces matching Python dataclasses from scitex.writer.dataclasses.results
 *
 * These ensure type safety and prevent silent failures in frontend-backend communication.
 */

/**
 * Response from save_sections_view API
 * Matches: scitex.writer.dataclasses.results.SaveSectionsResponse
 */
export interface SaveSectionsResponse {
  success: boolean;
  sections_saved: number;
  sections_skipped: number;
  message: string;
  errors: string[];
  error_details: Record<string, string>;
}

/**
 * Response from section_view API (GET/POST)
 * Matches: scitex.writer.dataclasses.results.SectionReadResponse
 */
export interface SectionReadResponse {
  success: boolean;
  content: string;
  section_name: string;
  section_id: string;
  doc_type: "manuscript" | "supplementary" | "revision" | "shared";
  file_path: string | null;
  error: string | null;
}

/**
 * Compilation result from compile_preview/compile_full APIs
 * Matches: scitex.writer.dataclasses.results.CompilationResult
 */
export interface CompilationResult {
  success: boolean;
  exit_code: number;
  stdout: string;
  stderr: string;
  output_pdf: string | null;
  diff_pdf: string | null;
  log_file: string | null;
  duration: number;
  errors: string[];
  warnings: string[];
}

/**
 * Type guard to check if response is SaveSectionsResponse
 */
export function isSaveSectionsResponse(obj: any): obj is SaveSectionsResponse {
  return (
    obj &&
    typeof obj.success === "boolean" &&
    typeof obj.sections_saved === "number" &&
    typeof obj.sections_skipped === "number" &&
    Array.isArray(obj.errors)
  );
}

/**
 * Type guard to check if response is SectionReadResponse
 */
export function isSectionReadResponse(obj: any): obj is SectionReadResponse {
  return (
    obj &&
    typeof obj.success === "boolean" &&
    typeof obj.content === "string" &&
    typeof obj.section_name === "string" &&
    typeof obj.section_id === "string" &&
    typeof obj.doc_type === "string"
  );
}

/**
 * Type guard to check if response is CompilationResult
 */
export function isCompilationResult(obj: any): obj is CompilationResult {
  return (
    obj &&
    typeof obj.success === "boolean" &&
    typeof obj.exit_code === "number" &&
    typeof obj.stdout === "string" &&
    typeof obj.stderr === "string"
  );
}

/**
 * Validate SaveSectionsResponse - throws Error if invalid
 */
export function validateSaveSectionsResponse(
  response: SaveSectionsResponse,
): void {
  if (response.success && response.sections_saved === 0) {
    throw new Error("Response marked as success but no sections were saved");
  }

  if (!response.success && response.errors.length === 0) {
    throw new Error("Response marked as failed but no errors provided");
  }

  if (response.sections_saved < 0) {
    throw new Error(
      `Invalid sections_saved: ${response.sections_saved} (must be >= 0)`,
    );
  }

  if (response.sections_skipped < 0) {
    throw new Error(
      `Invalid sections_skipped: ${response.sections_skipped} (must be >= 0)`,
    );
  }
}

/**
 * Validate SectionReadResponse - throws Error if invalid
 */
export function validateSectionReadResponse(
  response: SectionReadResponse,
): void {
  if (
    response.success &&
    !response.content &&
    !response.section_name.includes("compiled_pdf") &&
    !response.section_name.includes("compiled_tex")
  ) {
    throw new Error(
      `Response marked as success but content is empty for ${response.section_id}`,
    );
  }

  if (!response.success && !response.error) {
    throw new Error(
      `Response marked as failed but no error message for ${response.section_id}`,
    );
  }

  if (!response.section_name) {
    throw new Error("section_name cannot be empty");
  }

  if (!response.section_id) {
    throw new Error("section_id cannot be empty");
  }

  const validDocTypes = ["manuscript", "supplementary", "revision", "shared"];
  if (!validDocTypes.includes(response.doc_type)) {
    throw new Error(`Invalid doc_type: ${response.doc_type}`);
  }
}

// EOF
