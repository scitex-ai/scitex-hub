/**
 * Shared Utilities Index
 * Centralized export of all utility modules
 */

// CSRF utilities

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/ts/utils/index.ts loaded",
);
export { getCsrfToken, createHeadersWithCsrf } from "./csrf.ts";

// Storage utilities
export { StorageManager, globalStorage, writerStorage } from "./storage.ts";

// API client
export { ApiClient, apiClient } from "./api.ts";
export type { ApiRequestInit, ApiResponse } from "./api.ts";

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
} from "./ui.ts";
export type { ToastType } from "./ui.ts";
