/**
 * Auto-Response Manager for Claude Code CLI
 *
 * Polls the xterm.js terminal buffer, detects Claude Code CLI prompt states,
 * and automatically sends appropriate responses (e.g., "2" for permission prompts).
 *
 * Ported from emacs-claude-code/src/ecc-auto-response-core.el
 *
 * Safety features (all ported from Emacs):
 *   - Burst rate limiting (max N responses per time window)
 *   - Same-state deduplication delay
 *   - Position tracking to avoid re-sending at same buffer location
 *   - Y/N → Y/Y/N re-check (CLI renders options progressively)
 *   - Stuck-state watchdog + sending-p watchdog
 *   - Nil-state retry with wider buffer window
 *   - Periodic return sending as session keepalive
 *   - Send verification & retry for permission prompts
 *   - Idle-loop detection for waiting state
 *   - Content hash skip for unchanged buffers
 */

import {
  detectState,
  readTerminalBuffer,
  DETECTION_BUFFER_SIZE,
} from "./ClaudeStateDetector";
import {
  type AutoResponseConfig,
  type ClaudeState,
  type SendFn,
  type GetTermFn,
  type SentPosition,
  DEFAULT_CONFIG,
  simpleHash,
} from "./auto-response-config";

// Re-export for consumers
export type { AutoResponseConfig } from "./auto-response-config";

export class AutoResponseManager {
  private config: AutoResponseConfig;
  private enabled = false;
  private timerId: ReturnType<typeof setInterval> | null = null;
  private sendFn: SendFn;
  private getTermFn: GetTermFn;

  // Tracking state
  private lastState: ClaudeState = null;
  private lastResponseTime = 0;
  private responseTimestamps: number[] = [];
  private sentPositions: SentPosition[] = [];
  private sending = false;
  private sendingTimestamp = 0;

  // Stuck-state watchdog
  private stateFirstSeenTime = 0;
  private stateFirstSeenState: ClaudeState = null;

  // Nil-state retry (from Emacs)
  private nilStateStart = 0;

  // Content hash skip (from Emacs)
  private lastContentHash = 0;

  // Periodic return timer (from Emacs)
  private periodicTimerId: ReturnType<typeof setInterval> | null = null;

  // Idle-loop detection (from Emacs encouragement system)
  private idleLoopCount = 0;
  private lastWaitingResponseTime = 0;

  // Listeners
  private onStateChangeCallbacks: Array<
    (state: ClaudeState, enabled: boolean) => void
  > = [];
  private onResponseSentCallbacks: Array<
    (state: ClaudeState, response: string) => void
  > = [];

  constructor(
    sendFn: SendFn,
    getTermFn: GetTermFn,
    config?: Partial<AutoResponseConfig>,
  ) {
    this.sendFn = sendFn;
    this.getTermFn = getTermFn;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  // ── Public API ─────────────────────────────────────────────────────

  isEnabled(): boolean {
    return this.enabled;
  }

  enable(): void {
    if (this.enabled) return;
    this.enabled = true;
    this.resetTracking();
    this.startTimer();
    this.startPeriodicTimer();
    this.notifyStateChange(null);
    console.log("[AutoResponse] Enabled");
  }

  disable(): void {
    if (!this.enabled) return;
    this.enabled = false;
    this.stopTimer();
    this.stopPeriodicTimer();
    this.notifyStateChange(null);
    console.log("[AutoResponse] Disabled");
  }

  toggle(): boolean {
    if (this.enabled) {
      this.disable();
    } else {
      this.enable();
    }
    return this.enabled;
  }

  onStateChange(cb: (state: ClaudeState, enabled: boolean) => void): void {
    this.onStateChangeCallbacks.push(cb);
  }

  onResponseSent(cb: (state: ClaudeState, response: string) => void): void {
    this.onResponseSentCallbacks.push(cb);
  }

  updateConfig(partial: Partial<AutoResponseConfig>): void {
    this.config = { ...this.config, ...partial };
    if (this.enabled) {
      this.stopTimer();
      this.stopPeriodicTimer();
      this.startTimer();
      this.startPeriodicTimer();
    }
  }

  // ── Timer ──────────────────────────────────────────────────────────

  private startTimer(): void {
    this.stopTimer();
    this.timerId = setInterval(() => this.tick(), this.config.interval);
    setTimeout(() => this.tick(), 100);
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  private startPeriodicTimer(): void {
    this.stopPeriodicTimer();
    if (this.config.periodicInterval <= 0) return;
    this.periodicTimerId = setInterval(() => {
      if (!this.enabled || this.sending) return;
      const term = this.getTermFn();
      if (!term) return;
      const state = detectState(
        readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
      );
      if (state === "running") return;
      console.log("[AutoResponse] Periodic return (keepalive)");
      this.sendFn("\r");
    }, this.config.periodicInterval);
  }

  private stopPeriodicTimer(): void {
    if (this.periodicTimerId !== null) {
      clearInterval(this.periodicTimerId);
      this.periodicTimerId = null;
    }
  }

  // ── Core processing ────────────────────────────────────────────────

  private tick(): void {
    if (!this.enabled) return;

    // Sending-p watchdog: clear stuck sending flag (from Emacs)
    if (
      this.sending &&
      this.sendingTimestamp > 0 &&
      Date.now() - this.sendingTimestamp > this.config.sendingTimeout
    ) {
      console.log(
        `[AutoResponse] WATCHDOG: sending stuck for ${((Date.now() - this.sendingTimestamp) / 1000).toFixed(0)}s, clearing`,
      );
      this.sending = false;
    }
    if (this.sending) return;

    const term = this.getTermFn();
    if (!term) return;

    const bufferText = readTerminalBuffer(term, DETECTION_BUFFER_SIZE);
    if (!bufferText) return;

    // Content hash skip (from Emacs)
    const hash = simpleHash(bufferText);
    const contentChanged = hash !== this.lastContentHash;
    this.lastContentHash = hash;

    let state = detectState(bufferText);

    // Nil-state retry: widen detection window after timeout (from Emacs)
    if (!state) {
      if (this.nilStateStart === 0) {
        this.nilStateStart = Date.now();
      } else if (
        Date.now() - this.nilStateStart >
        this.config.nilStateRetryInterval
      ) {
        const wideText = readTerminalBuffer(
          term,
          DETECTION_BUFFER_SIZE * this.config.nilStateWideMultiplier,
        );
        state = detectState(wideText);
        if (state) {
          console.log(`[AutoResponse] Wide detection found: ${state}`);
        }
      }
    } else {
      this.nilStateStart = 0;
    }

    this.notifyStateChange(state);
    this.trackStateDuration(state);

    if (!state || state === "running" || state === "user_typing") return;

    // Skip unchanged content for non-actionable states (from Emacs)
    if (
      !contentChanged &&
      state !== "y_n" &&
      state !== "y_y_n" &&
      state !== "suggestion"
    ) {
      return;
    }

    if (this.alreadySentAtPosition(term)) return;
    if (this.shouldThrottle(state)) return;

    this.sendResponse(state, term);
  }

  private async sendResponse(state: ClaudeState, term: any): Promise<void> {
    if (!state) return;

    // Y/N re-check: wait and re-detect to avoid sending "1" when Y/Y/N
    let effectiveState = state;
    if (state === "y_n") {
      this.sending = true;
      this.sendingTimestamp = Date.now();
      await this.sleep(this.config.ynRecheckDelay);
      const recheck = detectState(
        readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
      );
      if (recheck === "y_y_n") {
        effectiveState = "y_y_n";
        console.log("[AutoResponse] Y/N upgraded to Y/Y/N after re-check");
      }
      this.sending = false;
    }

    // Idle-loop detection for waiting state (from Emacs encouragement)
    if (effectiveState === "waiting") {
      const now = Date.now();
      const elapsed = now - this.lastWaitingResponseTime;
      if (elapsed > this.config.minWorkDuration) {
        this.idleLoopCount = 0;
      }
      if (this.idleLoopCount >= this.config.idleLoopMax) {
        console.log("[AutoResponse] Idle loop detected, suppressing waiting");
        return;
      }
      this.idleLoopCount++;
      this.lastWaitingResponseTime = now;
    }

    const response = this.config.responses[effectiveState];
    if (response === undefined || response === null) return;

    this.sending = true;
    this.sendingTimestamp = Date.now();

    try {
      await this.sleep(this.config.safeDelay);

      if (response.length > 0) {
        this.sendFn(response);
      }
      await this.sleep(200);
      this.sendFn("\r");

      await this.sleep(this.config.safeDelay);

      this.updateTracking(effectiveState, term);
      this.notifyResponseSent(effectiveState, response);

      console.log(
        `[AutoResponse] Sent "${response || "↵"}" for state: ${effectiveState}`,
      );

      // Verify send succeeded; retry if needed (from Emacs retry module)
      await this.verifySend(effectiveState, term);
    } finally {
      this.sending = false;
    }
  }

  // ── Send verification (from Emacs ecc-auto-response-retry.el) ─────

  private async verifySend(state: ClaudeState, term: any): Promise<void> {
    const isPermission = state === "y_n" || state === "y_y_n";
    if (!isPermission) return;

    for (let i = 0; i < this.config.permissionRetryMax; i++) {
      await this.sleep(this.config.verifyDelay);
      const newState = detectState(
        readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
      );
      if (newState !== state) {
        console.log(`[AutoResponse] Verified: ${state} → ${newState}`);
        return;
      }
      console.log(
        `[AutoResponse] Retry ${i + 1}/${this.config.permissionRetryMax}: still ${state}`,
      );
      const response = this.config.responses[state];
      if (response !== undefined && response !== null) {
        if (response.length > 0) this.sendFn(response);
        await this.sleep(200);
        this.sendFn("\r");
      }
    }
  }

  // ── Throttling ─────────────────────────────────────────────────────

  private shouldThrottle(state: ClaudeState): boolean {
    const now = Date.now();

    if (
      state === this.lastState &&
      now - this.lastResponseTime < this.config.sameStateDelay
    ) {
      return true;
    }

    const windowStart = now - this.config.burstWindow;
    const recentCount = this.responseTimestamps.filter(
      (t) => t >= windowStart,
    ).length;
    return recentCount >= this.config.burstLimit;
  }

  private alreadySentAtPosition(term: any): boolean {
    const bufLen = term.buffer?.active?.length ?? 0;
    const threshold = 100;

    const currentState = detectState(
      readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
    );
    if (currentState !== this.lastState) return false;

    return this.sentPositions.some(
      (sp) => Math.abs(bufLen - sp.bufferLength) < threshold,
    );
  }

  // ── Watchdog ───────────────────────────────────────────────────────

  private trackStateDuration(state: ClaudeState): void {
    if (state && state === this.stateFirstSeenState) {
      if (
        (state === "y_n" || state === "y_y_n" || state === "waiting") &&
        this.stateFirstSeenTime > 0 &&
        Date.now() - this.stateFirstSeenTime > this.config.stuckStateThreshold
      ) {
        console.log(
          `[AutoResponse] WATCHDOG: state ${state} stuck for ${((Date.now() - this.stateFirstSeenTime) / 1000).toFixed(0)}s, forcing re-send`,
        );
        this.stateFirstSeenTime = Date.now();
        this.sentPositions = [];
        const term = this.getTermFn();
        if (term) this.sendResponse(state, term);
      }
    } else {
      this.stateFirstSeenState = state;
      this.stateFirstSeenTime = state ? Date.now() : 0;
    }
  }

  // ── Tracking helpers ───────────────────────────────────────────────

  private updateTracking(state: ClaudeState, term: any): void {
    const now = Date.now();
    this.lastState = state;
    this.lastResponseTime = now;
    this.responseTimestamps.push(now);

    const bufLen = term.buffer?.active?.length ?? 0;
    this.sentPositions.push({ bufferLength: bufLen, time: now });

    const cutoff = now - 60000;
    this.responseTimestamps = this.responseTimestamps.filter(
      (t) => t >= cutoff,
    );
    this.sentPositions = this.sentPositions.filter((sp) => sp.time >= cutoff);
  }

  private resetTracking(): void {
    this.lastState = null;
    this.lastResponseTime = 0;
    this.responseTimestamps = [];
    this.sentPositions = [];
    this.sending = false;
    this.sendingTimestamp = 0;
    this.stateFirstSeenTime = 0;
    this.stateFirstSeenState = null;
    this.nilStateStart = 0;
    this.lastContentHash = 0;
    this.idleLoopCount = 0;
    this.lastWaitingResponseTime = 0;
  }

  // ── Notifications ──────────────────────────────────────────────────

  private notifyStateChange(state: ClaudeState): void {
    for (const cb of this.onStateChangeCallbacks) {
      try {
        cb(state, this.enabled);
      } catch (e) {
        console.error("[AutoResponse] State change callback error:", e);
      }
    }
  }

  private notifyResponseSent(state: ClaudeState, response: string): void {
    for (const cb of this.onResponseSentCallbacks) {
      try {
        cb(state, response);
      } catch (e) {
        console.error("[AutoResponse] Response sent callback error:", e);
      }
    }
  }

  // ── Utility ────────────────────────────────────────────────────────

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
