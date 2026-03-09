/**
 * Doctype Change Handler
 * Handles document type dropdown changes
 */

import {
  handleDocTypeSwitch,
  populateSectionDropdownDirect,
} from "../../../utils/index";
import { getDoctypeFolder } from "./TreeConfiguration";


export interface DoctypeChangeDependencies {
  editor: any;
  sectionsManager: any;
  state: any;
  pdfPreviewManager: any;
  statePersistence: any;
  compilationManager?: any;
}

/**
 * Setup doctype change handler with file tree
 */
export function setupDoctypeChangeWithTree(
  docTypeSelector: HTMLSelectElement,
  filesTree: any,
  writerFilter: any,
  deps: DoctypeChangeDependencies,
): void {
  docTypeSelector.addEventListener("change", (e) => {
    const newDocType = (e.target as HTMLSelectElement).value;
    console.log("[DoctypeChangeHandler] Document type changed to:", newDocType);

    if (deps.editor && deps.state.currentSection) {
      // Save current section before switching
      const currentContent = deps.editor.getContent();
      deps.sectionsManager.setContent(
        deps.state.currentSection,
        currentContent,
      );

      // Update state with new document type
      deps.state.currentDocType = newDocType;

      // Save doctype to persistence
      deps.statePersistence.saveDoctype(newDocType);
      console.log(
        "[DoctypeChangeHandler] Saved doctype to persistence:",
        newDocType,
      );

      // Update filter with new doctype
      writerFilter.setDoctype(newDocType);

      // Update PDF preview manager to use the new document type
      deps.pdfPreviewManager.setDocType(newDocType);

      // Switch to first section of the new document type
      handleDocTypeSwitch(
        deps.editor,
        deps.sectionsManager,
        deps.state,
        newDocType,
      );

      // Tree is shared across modules - do not auto-navigate it from editor
    }
  });
}

/**
 * Setup doctype change handler without file tree (dropdown only)
 */
export function setupDoctypeChangeWithoutTree(
  docTypeSelector: HTMLSelectElement,
  onFileSelectHandler: (sectionId: string, sectionName: string) => void,
  deps: DoctypeChangeDependencies,
): void {
  docTypeSelector.addEventListener("change", async (e) => {
    const newDocType = (e.target as HTMLSelectElement).value;
    console.log(
      "[DoctypeChangeHandler] Document type changed to:",
      newDocType,
      "- updating section dropdown",
    );

    // Save current section content before switching
    if (deps.editor && deps.state.currentSection) {
      const currentContent = deps.editor.getContent();
      deps.sectionsManager.setContent(
        deps.state.currentSection,
        currentContent,
      );
    }

    // Update state
    deps.state.currentDocType = newDocType;

    // Save doctype to persistence
    deps.statePersistence.saveDoctype(newDocType);
    console.log(
      "[DoctypeChangeHandler] Saved doctype to persistence:",
      newDocType,
    );

    // Update PDF preview manager doc type
    if (deps.pdfPreviewManager) {
      deps.pdfPreviewManager.setDocType(newDocType);
    }

    // Repopulate section dropdown for new doc_type
    await populateSectionDropdownDirect(
      newDocType,
      onFileSelectHandler,
      deps.compilationManager,
      deps.state,
    );
  });

  console.log("[DoctypeChangeHandler] Doc type change handler attached");
}
