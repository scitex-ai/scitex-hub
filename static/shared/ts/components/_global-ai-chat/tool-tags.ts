/**
 * Tool tag rendering for AI chat message bubbles.
 */

export function appendToolTags(msgEl: HTMLElement, tools: string[]): void {
  let toolsDiv = msgEl.querySelector<HTMLElement>(".stx-shell-ai-tools");
  if (!toolsDiv) {
    toolsDiv = document.createElement("div");
    toolsDiv.className = "stx-shell-ai-tools";
    msgEl.appendChild(toolsDiv);
  }
  for (const name of tools) {
    const tag = document.createElement("span");
    tag.className = "stx-shell-ai-tool-tag";
    tag.textContent = name;
    toolsDiv.appendChild(tag);
  }
}
