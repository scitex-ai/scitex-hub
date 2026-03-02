/**
 * Auto-Response Configuration & Types
 *
 * Extracted from AutoResponseManager to keep files under 512 lines.
 * Mirrors the Emacs ecc-auto-response.el configuration variables.
 */

import type { ClaudeState } from "./ClaudeStateDetector";

// ── Utility ──────────────────────────────────────────────────────────

/** Simple string hash for content-change detection. */
export function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return hash;
}

// ── Types ──────────────────────────────────────────────────────────────

export interface SentPosition {
  bufferLength: number;
  time: number;
}

export type SendFn = (text: string) => void;
export type GetTermFn = () => any | null;

// ── Configuration ──────────────────────────────────────────────────────

export interface AutoResponseConfig {
  /** Polling interval in milliseconds. */
  interval: number;
  /** Responses to send for each state. null = skip. */
  responses: Record<string, string | null>;
  /** Min ms between responses to the same state. */
  sameStateDelay: number;
  /** Max responses in burst window. */
  burstLimit: number;
  /** Burst window in ms. */
  burstWindow: number;
  /** Safety delay before/after sending (ms). */
  safeDelay: number;
  /** Delay before Y/N re-check to detect Y/Y/N upgrade (ms). */
  ynRecheckDelay: number;
  /** Ms before watchdog forces re-send on stuck state. */
  stuckStateThreshold: number;
  /** Timeout for sending-p watchdog (ms). Clears stuck sending flag. */
  sendingTimeout: number;
  /** Ms of nil-state before retrying detection with wider buffer. */
  nilStateRetryInterval: number;
  /** Buffer size multiplier for wider nil-state detection. */
  nilStateWideMultiplier: number;
  /** Periodic return interval (ms). 0 = disabled. */
  periodicInterval: number;
  /** Delay before verifying send success (ms). */
  verifyDelay: number;
  /** Max retries for permission prompts after failed send. */
  permissionRetryMax: number;
  /** Max consecutive idle waiting responses before suppression. */
  idleLoopMax: number;
  /** Min ms of real work between waiting responses to reset idle counter. */
  minWorkDuration: number;
}

export const DEFAULT_CONFIG: AutoResponseConfig = {
  interval: 1500,
  responses: {
    y_n: "1",
    y_y_n: "2",
    waiting: "/speak-signature", // From Emacs encouragement system
    suggestion: "", // Send Enter (empty string = just Return)
  },
  sameStateDelay: 1500,
  burstLimit: 10,
  burstWindow: 3000,
  safeDelay: 500,
  ynRecheckDelay: 1000,
  stuckStateThreshold: 15000,
  sendingTimeout: 30000,
  nilStateRetryInterval: 5000,
  nilStateWideMultiplier: 4,
  periodicInterval: 300000, // 5 minutes
  verifyDelay: 2000,
  permissionRetryMax: 1,
  idleLoopMax: 3,
  minWorkDuration: 30000,
};

// Re-export ClaudeState for convenience
export type { ClaudeState };
