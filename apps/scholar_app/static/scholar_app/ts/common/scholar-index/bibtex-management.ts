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
export function resetBibtexForm() {
    const formArea = document.getElementById("bibtexFormArea");
    const progressArea = document.getElementById("bibtexProgressArea");
    const form = document.getElementById("bibtexEnrichmentForm");
    if (formArea)
        formArea.style.display = "block";
    if (progressArea)
        progressArea.style.display = "none";
    if (form)
        form.reset();
}
/**
 * Poll BibTeX job status
 * @param jobId - The job ID to poll
 * @param attempts - Number of polling attempts (default: 0)
 */
export function pollBibtexJobStatus(jobId, attempts = 0) {
    console.log("[BibTeX Management] pollBibtexJobStatus called with jobId:", jobId);
    // Implementation note: This function is defined here for module organization.
    // The actual polling logic should be implemented based on your API endpoints.
}
window.resetBibtexForm = resetBibtexForm;
//# sourceMappingURL=bibtex-management.ts.map
