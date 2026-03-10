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
