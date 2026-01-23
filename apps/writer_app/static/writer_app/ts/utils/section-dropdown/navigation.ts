/**
 * Section Navigation
 * Handles document type switching and section navigation
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/section-dropdown/navigation.ts loaded",
);

/**
 * Handle document type switch - navigates to first section of new doc type
 *
 * @param editor - Writer editor instance
 * @param sectionsManager - Sections manager instance
 * @param state - Application state
 * @param newDocType - New document type to switch to
 */
export function handleDocTypeSwitch(
  editor: any,
  sectionsManager: any,
  state: any,
  newDocType: string,
): void {
  // Map of first section for each document type
  const firstSectionByDocType: { [key: string]: string } = {
    shared: "title", // Shared sections: title, authors, keywords, journal_name
    manuscript: "abstract",
    supplementary: "content",
    revision: "response",
  };

  const firstSection = firstSectionByDocType[newDocType] || "abstract";

  if (!firstSection) {
    console.warn(
      "[Writer] No sections available for document type:",
      newDocType,
    );
    console.log("[Writer] Keeping current section:", state.currentSection);
    // Don't switch sections if document type has no sections
    return;
  }

  // Switch to the first section of the new document type
  console.log("[Writer] Switching to", firstSection, "for", newDocType);
  // Import switchSection dynamically to avoid circular dependency
  import("../../writer/index.js").then(({ switchSection }) => {
    switchSection(editor, sectionsManager, state, firstSection);
  });
}
