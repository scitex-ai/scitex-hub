/**
 * Model badge display and current-model fetch for the AI chat panel.
 *
 * Display names are derived dynamically by the backend from LiteLLM
 * and LLM_PROVIDERS registry — no hardcoded model names here.
 */

import { API_URLS } from "../../utils/api-urls";

const MODEL_KEY = "scitex_ai_model";
const MODEL_DISPLAY_KEY = "scitex_ai_model_display";

export { MODEL_KEY };

export function fetchCurrentModel(
  onModel: (name: string, campaign?: boolean, display?: string) => void,
): void {
  fetch(API_URLS.llm.model)
    .then((r) => r.json())
    .then((data) => {
      if (data.success && data.model)
        onModel(data.model, data.campaign, data.display);
    })
    .catch(() => {});
}

export function setModelBadge(
  badge: HTMLElement | null,
  modelName: string,
  campaign?: boolean,
  displayName?: string,
): void {
  if (!badge) return;
  if (!modelName || modelName === "undefined" || modelName === "null") {
    badge.innerHTML =
      '<a href="/accounts/settings/ai-providers/" class="ai-model-configure-link">' +
      '<i class="fas fa-cog"></i> Configure AI Provider</a>';
    badge.title = "No AI provider configured — click to set up";
    return;
  }
  // Use backend-provided display name; fallback to raw model string
  const display = displayName || modelName;
  const suffix = campaign ? " (Campaign)" : "";
  badge.textContent = display + suffix;
  badge.title = campaign ? `${modelName} — Campaign mode (limited)` : modelName;
  sessionStorage.setItem(MODEL_KEY, modelName);
  if (displayName) sessionStorage.setItem(MODEL_DISPLAY_KEY, displayName);
}
