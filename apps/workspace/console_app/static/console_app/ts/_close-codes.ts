/**
 * WebSocket close code classification for terminal connections.
 *
 * Maps SLURM/broker-specific codes to user-facing messages
 * and reconnect policy.
 */

export interface CloseClassification {
  message: string;
  reconnect: boolean;
}

export function classifyCloseCode(event: CloseEvent): CloseClassification {
  switch (event.code) {
    case 1000:
      return {
        message: "Connection closed, reconnecting...",
        reconnect: true,
      };
    case 1001:
      return {
        message: "Server going away (maintenance or restart)",
        reconnect: true,
      };
    case 1006:
      return { message: "Connection lost (network issue)", reconnect: true };
    case 1011:
      return { message: "Server error", reconnect: true };
    case 1012:
      return { message: "Server restarting", reconnect: true };
    case 1013:
      return {
        message: "Server overloaded, try again later",
        reconnect: true,
      };
    case 4000:
      return { message: "Authentication required", reconnect: false };
    case 4001:
      return { message: "Access denied", reconnect: false };
    case 4002:
      return { message: "Project not found", reconnect: false };
    case 4003:
      return { message: "Terminal unavailable", reconnect: false };
    case 4010:
      return {
        message: "Computing resources temporarily busy",
        reconnect: true,
      };
    default:
      return {
        message: event.reason || `Connection closed (${event.code})`,
        reconnect: true,
      };
  }
}

// EOF
