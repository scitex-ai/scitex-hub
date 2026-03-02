/**
 * Section Dropdown Module
 * Re-exports all section dropdown functionality
 */

export {
  populateSectionDropdownDirect,
  syncDropdownToSection,
  syncDropdownsFromPath,
} from "./SectionDropdown";

export { handleDocTypeSwitch } from "./navigation";

export { renderSectionDropdown } from "./rendering";

export {
  toggleSectionVisibility,
  setupSectionEvents,
} from "./events";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/_section-dropdown/index.ts loaded",
);
