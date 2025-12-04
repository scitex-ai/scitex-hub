/**
 * Shared Utilities Index
 * Centralized export of all utility modules
 */

// CSRF utilities

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/ts/utils/index.ts loaded",
);
export { getCsrfToken, createHeadersWithCsrf } from "./csrf.js";

// Storage utilities
export { StorageManager, globalStorage, writerStorage } from "./storage.js";

// API client
export { ApiClient, apiClient } from "./api.js";
export type { ApiRequestInit, ApiResponse } from "./api.js";

// UI utilities
export {
  showToast,
  showStatus,
  setButtonLoading,
  showSpinner,
  Modal,
  confirm,
  debounce,
  throttle,
} from "./ui.js";
export type { ToastType } from "./ui.js";
