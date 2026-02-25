/**
 * Model badge display and current-model fetch for the AI chat panel.
 */

const MODEL_KEY = "scitex_ai_model";

export { MODEL_KEY };

export function fetchCurrentModel(
  onModel: (name: string, campaign?: boolean) => void,
): void {
  fetch("/llm/api/model/")
    .then((r) => r.json())
    .then((data) => {
      if (data.success && data.model) onModel(data.model, data.campaign);
    })
    .catch(() => {});
}

export function setModelBadge(
  badge: HTMLElement | null,
  modelName: string,
  campaign?: boolean,
): void {
  if (!badge) return;
  let display = modelName.includes("/")
    ? modelName.split("/").slice(1).join("/")
    : modelName;
  if (campaign) display += " (Campaign)";
  badge.textContent = display;
  badge.title = campaign ? `${modelName} — Campaign mode (limited)` : modelName;
  sessionStorage.setItem(MODEL_KEY, modelName);
}
