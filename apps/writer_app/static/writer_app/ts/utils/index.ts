/**
 * Writer-specific utility modules
 * These utilities are shared across writer components
 */

// DOM utilities

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/index.ts loaded",
);
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
} from "./dom.utils.ts";

// Keyboard utilities
export {
  matchesShortcut,
  registerShortcut,
  formatShortcut,
  isInputElement,
  type KeyboardShortcut,
} from "./keyboard.utils.ts";

// LaTeX utilities
export {
  convertToLatex,
  convertFromLatex,
  extractTextFromLatex,
  isLatexContent,
  validateLatexSyntax,
} from "./latex.utils.ts";

// Timer and timing utilities
export {
  debounce,
  throttle,
  formatElapsedTime,
  SimpleTimer,
  wait,
  createTimeout,
} from "./timer.utils.ts";

// UI utilities
export {
  showToast,
  getUserContext,
  updateWordCountDisplay,
  updateSectionTitleLabel,
  updatePDFPreviewTitle,
  updateCommitButtonVisibility,
} from "./ui.ts";

// Compilation UI utilities
export {
  showCompilationProgress,
  hideCompilationProgress,
  updateCompilationProgress,
  appendCompilationLog,
  updateCompilationLog,
  showCompilationSuccess,
  showCompilationError,
  minimizeCompilationOutput,
  restoreCompilationOutput,
  compilationLogs,
  toggleCompilationPanel,
  togglePreviewLog,
  toggleFullLog,
  handleCompilationLogStart,
  handleCompilationLogStop,
  handleCompilationLogClose,
  updateMinimizedStatus,
  updateStatusLamp,
  updateSlimProgress,
  toggleCompilationDetails,
  restoreCompilationStatus,
} from "./compilation-ui.ts";

// Section dropdown utilities
export {
  populateSectionDropdownDirect,
  syncDropdownToSection,
  syncDropdownsFromPath,
  handleDocTypeSwitch,
  toggleSectionVisibility,
} from "./section-dropdown/index.ts";

// Section management utilities
export {
  setupSectionListeners,
  loadSectionContent,
  switchSection,
  updateSectionUI,
  loadCompiledPDF,
  setupSectionManagementButtons,
  clearCompileTimeout,
} from "./section-management.ts";

// Compilation handler utilities
export {
  setupCompilationListeners,
  handleCompileFull,
  handleCompile,
} from "./compilation-handlers.ts";

// Panel management utilities
export {
  setupSidebarButtons,
  setupPDFZoomControls,
  openPDF,
  loadPanelCSS,
  switchRightPanel,
} from "./panel-management.ts";
