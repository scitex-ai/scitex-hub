/**
 * Writer-specific utility modules
 * These utilities are shared across writer components
 */

// DOM utilities

export {
  querySelector,
  querySelectorAll,
  setVisibility,
  toggleClass,
  addClass,
  removeClass,
  hasClass,
  getComputedStyle,
  setAttributes,
  removeElement,
  clearElement,
  createElement,
  scrollIntoView,
  getScrollPosition,
  setScrollPosition,
} from "./_dom.utils";

// Keyboard utilities
export {
  matchesShortcut,
  registerShortcut,
  formatShortcut,
  isInputElement,
  type KeyboardShortcut,
} from "./_keyboard.utils";

// LaTeX utilities
export {
  convertToLatex,
  convertFromLatex,
  extractTextFromLatex,
  isLatexContent,
  validateLatexSyntax,
} from "./latex.utils";

// Timer and timing utilities
export {
  debounce,
  throttle,
  formatElapsedTime,
  SimpleTimer,
  wait,
  createTimeout,
} from "./_timer.utils";

// UI utilities
export {
  showToast,
  getUserContext,
  updateWordCountDisplay,
  updateSectionTitleLabel,
  updatePDFPreviewTitle,
  updateCommitButtonVisibility,
} from "./ui";

// Compilation UI utilities
export {
  showCompilationProgress,
  hideCompilationProgress,
  updateCompilationProgress,
  appendCompilationLog,
  updateCompilationLog,
  showCompilationSuccess,
  showCompilationError,
  compilationLogs,
  togglePreviewLog,
  toggleFullLog,
  setActiveLogType,
  getActiveLogType,
  updateStatusLamp,
  updateSlimProgress,
  restoreCompilationStatus,
} from "./compilation-ui";

// Section dropdown utilities
export {
  populateSectionDropdownDirect,
  syncDropdownToSection,
  syncDropdownsFromPath,
  handleDocTypeSwitch,
  toggleSectionVisibility,
} from "./_section-dropdown/index";

// Section management utilities
export {
  setupSectionListeners,
  loadSectionContent,
  switchSection,
  updateSectionUI,
  loadCompiledPDF,
  setupSectionManagementButtons,
  clearCompileTimeout,
} from "./section-management";

// Compilation handler utilities
export {
  setupCompilationListeners,
  handleCompileFull,
  handleCompile,
} from "./compilation-handlers";

// Panel management utilities
export {
  setupSidebarButtons,
  setupPDFZoomControls,
  openPDF,
  loadPanelCSS,
  switchRightPanel,
} from "./panel-management";
