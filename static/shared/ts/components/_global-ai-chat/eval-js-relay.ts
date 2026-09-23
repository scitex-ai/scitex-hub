/**
 * JS Eval WebSocket Relay
 *
 * Connects to ws://.../ws/llm/eval-js/ to receive JavaScript evaluation
 * requests from MCP tools. Evaluates the code in the browser context
 * and sends the result back.
 */

import { runUIActions, UIActionArgs } from "../ui-action/index";

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 3000;
const MAX_RECONNECT_MS = 60000;

function getWsUrl(): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws/llm/eval-js/`;
}

function handleEvalJs(data: { code: string; request_id: string }): void {
  console.error(
    "[eval-js] exec rid=" + data.request_id + " code=" + String(data.code).slice(0, 80),
  );
  let result: unknown;
  try {
    result = new Function(data.code)();
  } catch (err) {
    result = { error: String(err) };
  }

  const payload = JSON.stringify({
    type: "eval_js_result",
    request_id: data.request_id,
    result: result === undefined ? null : result,
    code_echo: String(data.code).slice(0, 120),
    agent: "relay-v3",
  });
  // Primary: WebSocket upstream.
  if (ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(payload);
    } catch (err) {
      console.error("[eval-js] ws.send failed: " + String(err));
    }
  }
  // Fallback: plain HTTPS POST (same-origin, session auth). The legacy
  // socket upstream silently drops frames in some environments; the
  // result must not depend on it.
  try {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    void fetch("/apps/llm/api/eval-result/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(m ? { "X-CSRFToken": m[1] } : {}),
      },
      body: payload,
      keepalive: true,
    });
  } catch (err) {
    console.error("[eval-js] result POST failed: " + String(err));
  }
}

function handleUiAction(data: { steps: unknown[]; delay_ms: number }): void {
  void runUIActions({
    steps: data.steps,
    delay_ms: data.delay_ms,
  } as UIActionArgs);
}

function onMessage(event: MessageEvent): void {
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(event.data as string) as Record<string, unknown>;
  } catch {
    return;
  }

  switch (data.type) {
    case "eval_js":
      handleEvalJs(data as unknown as { code: string; request_id: string });
      break;
    case "ui_action":
      handleUiAction(data as unknown as { steps: unknown[]; delay_ms: number });
      break;
  }
}

function connect(): void {
  if (ws) return;

  ws = new WebSocket(getWsUrl());

  ws.addEventListener("open", () => {
    reconnectDelay = 3000; // Reset backoff on successful connect
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  });

  ws.addEventListener("message", onMessage);

  ws.addEventListener("close", () => {
    ws = null;
    scheduleReconnect();
  });

  ws.addEventListener("error", () => {
    ws?.close();
  });
}

function scheduleReconnect(): void {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_MS);
}

/**
 * Initialize the eval-js WebSocket relay.
 * Call once when the page loads (after authentication).
 */
export function initEvalJsRelay(): void {
  connect();
}
