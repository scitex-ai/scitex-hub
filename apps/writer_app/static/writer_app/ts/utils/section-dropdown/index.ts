/**
 * Section Dropdown Module
 * Re-exports all section dropdown functionality
 */

export {
  populateSectionDropdownDirect,
  syncDropdownToSection,
  syncDropdownsFromPath,
} from "./SectionDropdown.js";

export { handleDocTypeSwitch } from "./navigation.js";

export { renderSectionDropdown } from "./rendering.js";

export {
  toggleSectionVisibility,
  setupSectionEvents,
} from "./events.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/section-dropdown/index.ts loaded",
);
