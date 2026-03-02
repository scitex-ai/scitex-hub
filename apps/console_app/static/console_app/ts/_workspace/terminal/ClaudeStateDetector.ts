/**
 * Claude Code CLI State Detector
 *
 * Detects Claude Code CLI prompt states from terminal buffer content.
 * Ported from emacs-claude-code/src/ecc-state-detection.el
 *
 * States detected (in priority order):
 *   y_y_n      — 3-choice permission prompt (Yes / Yes-and / No)
 *   suggestion — Edit suggestion (↵ send)
 *   y_n        — 2-choice Yes/No prompt
 *   running    — Claude is working
 *   user_typing— User has started typing at prompt
 *   waiting    — Claude waiting for user input
 */

export type ClaudeState =
  | "y_y_n"
  | "suggestion"
  | "y_n"
  | "running"
  | "user_typing"
  | "waiting"
  | null;

// ── Detection patterns (mirrored from ecc-state-detection.el) ──────────

const Y_Y_N_PATTERNS = [
  "2. Yes, and",
  "2. Yes, allow",
  "2. Yes, auto-accept",
  "2. Yes, don't ask",
  "2. Yes, and don't",
];

const Y_N_PATTERNS = ["❯ 1. Yes", "❯ 1. Yes"];

const SUGGESTION_PATTERNS = ["↵ send"];

const RUNNING_PATTERNS = [
  "(esc to interrupt",
  "tokens ·",
  "· thinking",
  "ing…",
  "· thought for ",
];

const WAITING_PATTERNS = [
  "Crunched for",
  "Sautéed for",
  "Cogitated for",
  "Whipped up",
  "Brewed for",
  "Cooked for",
  "Marinated for",
  "Stewed for",
  "Baked for",
  "Simmered for",
  "Crafted for",
  "Distilled for",
  "❯ ",
  "❯ ",
  "> ",
  "> ",
  "❯ ",
];

// Prompt prefixes — if prompt + printable char detected, user is typing
const PROMPT_PREFIXES = ["❯ "];

/** Number of characters from end of buffer to check. */
export const DETECTION_BUFFER_SIZE = 2048;

// ── Helpers ────────────────────────────────────────────────────────────

/** Normalize unicode whitespace to regular spaces for reliable matching. */
function normalizeText(text: string): string {
  return text
    .replace(/\u00a0/g, " ")
    .replace(/[\u2000-\u200b\u202f\u205f\u3000]/g, " ");
}

function matchPatterns(patterns: string[], text: string): string | null {
  const normalized = normalizeText(text);
  for (const pattern of patterns) {
    if (normalized.includes(normalizeText(pattern))) {
      return pattern;
    }
  }
  return null;
}

function isUserTyping(text: string): boolean {
  const lines = text.split("\n").filter((l) => l.length > 0);
  if (lines.length === 0) return false;
  const lastLine = normalizeText(lines[lines.length - 1]);

  for (const prefix of PROMPT_PREFIXES) {
    const normalizedPrefix = normalizeText(prefix);
    if (lastLine.includes(normalizedPrefix)) {
      // Check if there is a printable non-space char after the prefix
      const idx = lastLine.lastIndexOf(normalizedPrefix);
      const after = lastLine.slice(idx + normalizedPrefix.length);
      if (after.length > 0 && /[!-~]/.test(after.charAt(0))) {
        return true;
      }
    }
  }
  return false;
}

// ── Public API ─────────────────────────────────────────────────────────

/**
 * Detect Claude Code CLI state from terminal buffer text.
 *
 * @param bufferText  Last ~2048 chars of the terminal buffer.
 * @returns Detected state or null if no match.
 */
export function detectState(bufferText: string): ClaudeState {
  // Priority 1: Y/Y/N (permission prompts with 3 choices)
  if (matchPatterns(Y_Y_N_PATTERNS, bufferText)) return "y_y_n";

  // Priority 2: Suggestion (edit suggestion)
  if (matchPatterns(SUGGESTION_PATTERNS, bufferText)) return "suggestion";

  // Priority 3: Y/N (permission prompts with 2 choices)
  if (matchPatterns(Y_N_PATTERNS, bufferText)) return "y_n";

  // Priority 4: Running
  if (matchPatterns(RUNNING_PATTERNS, bufferText)) return "running";

  // Priority 5: User typing (prompt + printable char)
  if (isUserTyping(bufferText)) return "user_typing";

  // Priority 6: Waiting
  if (matchPatterns(WAITING_PATTERNS, bufferText)) return "waiting";

  return null;
}

/**
 * Read the last N characters from an xterm.js terminal buffer.
 */
export function readTerminalBuffer(
  term: any,
  maxChars: number = DETECTION_BUFFER_SIZE,
): string {
  const buf = term.buffer?.active;
  if (!buf) return "";

  const lines: string[] = [];
  let totalChars = 0;

  // Read from bottom to top
  for (let i = buf.length - 1; i >= 0 && totalChars < maxChars; i--) {
    const line = buf.getLine(i);
    if (!line) continue;
    const text = line.translateToString(true);
    lines.unshift(text);
    totalChars += text.length + 1; // +1 for newline
  }

  const result = lines.join("\n");
  // Trim to maxChars from the end
  return result.length > maxChars
    ? result.slice(result.length - maxChars)
    : result;
}
