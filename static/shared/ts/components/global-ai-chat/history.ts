/**
 * Command history for the AI chat input (bash-style C-p / C-n navigation).
 */

const HISTORY_KEY = "scitex_ai_history";
const MAX_HISTORY = 50;

export function loadHistory(): string[] {
  try {
    const saved = sessionStorage.getItem(HISTORY_KEY);
    return saved ? (JSON.parse(saved) as string[]) : [];
  } catch {
    return [];
  }
}

export function pushHistory(history: string[], text: string): string[] {
  if (!text || text === history[0]) return history; // deduplicate consecutive
  const next = [text, ...history].slice(0, MAX_HISTORY);
  try {
    sessionStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  } catch {
    /* storage full — ignore */
  }
  return next;
}
