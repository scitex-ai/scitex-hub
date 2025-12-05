/**
 * Shared Utilities Index
 * Centralized export of all utility modules
 */

// CSRF utilities

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/ts/utils/index.ts loaded",
);
export { getCsrfToken, createHeadersWithCsrf } from "./csrf";

// Storage utilities
export { StorageManager, globalStorage, writerStorage } from "./storage";

// API client
export { ApiClient, apiClient } from "./api";
export type { ApiRequestInit, ApiResponse } from "./api";

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
} from "./ui";
export type { ToastType } from "./ui";
