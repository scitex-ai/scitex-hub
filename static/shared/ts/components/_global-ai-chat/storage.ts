/**
 * sessionStorage helpers for AI Agent conversation persistence.
 */

const STORAGE_KEY = "scitex_ai_conversation";
export const MAX_STORED = 40;

export interface MediaRef {
  type: string;
  path: string;
  ext: string;
}

export interface StoredMessage {
  role: "user" | "assistant" | "error";
  text: string;
  toolsUsed?: string[];
  media?: MediaRef[];
}

export function saveMessage(msg: StoredMessage): void {
  const stored = loadMessages();
  stored.push(msg);
  if (stored.length > MAX_STORED) stored.splice(0, stored.length - MAX_STORED);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
}

export function loadMessages(): StoredMessage[] {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
}

export function clearMessages(): void {
  localStorage.removeItem(STORAGE_KEY);
}
