/**
 * MCP status badge: checks server health and shows MCP availability.
 * MCP runs locally in user containers via `scitex mcp start`.
 */

export function fetchMcpStatus(badge: HTMLElement | null): void {
  if (!badge) return;

  fetch("/healthz/")
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "healthy") {
        badge.classList.add("healthy");
        badge.classList.remove("error");
        const countEl = badge.querySelector(".ai-mcp-count");
        if (countEl) countEl.textContent = "available";
        badge.title = "MCP: server healthy — tools run in your container";
      } else {
        badge.classList.add("error");
        badge.classList.remove("healthy");
        const countEl = badge.querySelector(".ai-mcp-count");
        if (countEl) countEl.textContent = "offline";
        badge.title = "Server unavailable";
      }
    })
    .catch(() => {
      badge.classList.add("error");
      badge.classList.remove("healthy");
      const countEl = badge.querySelector(".ai-mcp-count");
      if (countEl) countEl.textContent = "error";
    });
}
