/**
 * BibTeX Management Module
 *
 * Handles BibTeX form reset and job status polling functionality.
 *
 * @module bibtex-management
 */

/**
 * Reset BibTeX form to initial state
 */
export function resetBibtexForm(): void {
  const formArea = document.getElementById(
    "bibtexFormArea",
  ) as HTMLElement | null;
  const progressArea = document.getElementById(
    "bibtexProgressArea",
  ) as HTMLElement | null;
  const form = document.getElementById(
    "bibtexEnrichmentForm",
  ) as HTMLFormElement | null;

  if (formArea) formArea.style.display = "block";
  if (progressArea) progressArea.style.display = "none";
  if (form) form.reset();
}

/**
 * Poll BibTeX job status
 * @param jobId - The job ID to poll
 * @param attempts - Number of polling attempts (default: 0)
 */
export function pollBibtexJobStatus(jobId: string, attempts: number = 0): void {
  console.log(
    "[BibTeX Management] pollBibtexJobStatus called with jobId:",
    jobId,
  );
  // Implementation note: This function is defined here for module organization.
  // The actual polling logic should be implemented based on your API endpoints.
}

// Export resetBibtexForm to global window object for backwards compatibility
declare global {
  interface Window {
    resetBibtexForm?: () => void;
  }
}

window.resetBibtexForm = resetBibtexForm;
