/**
 * Section Dropdown Module
 * Re-exports all section dropdown functionality
 */

export {
  populateSectionDropdownDirect,
  syncDropdownToSection,
  syncDropdownsFromPath,
} from "./SectionDropdown.ts";

export { handleDocTypeSwitch } from "./navigation.ts";

export { renderSectionDropdown } from "./rendering.ts";

export {
  toggleSectionVisibility,
  setupSectionEvents,
} from "./events.ts";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/section-dropdown/index.ts loaded",
);
