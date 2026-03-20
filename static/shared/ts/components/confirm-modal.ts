/**
 * Re-export from scitex-ui — the canonical implementation.
 * scitex-cloud consumers should import from "@/components/confirm-modal".
 */
export { showConfirm } from "scitex-ui/ts/app/confirm-modal";
export type { ConfirmModalOptions } from "scitex-ui/ts/app/confirm-modal";

import { showConfirm } from "scitex-ui/ts/app/confirm-modal";

// Keep global available for non-module scripts
declare global {
  interface Window {
    scitexConfirm: typeof showConfirm;
  }
}
window.scitexConfirm = showConfirm;
