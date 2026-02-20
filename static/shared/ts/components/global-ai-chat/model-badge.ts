/**
 * Model badge display and current-model fetch for the AI chat panel.
 */

const MODEL_KEY = "scitex_ai_model";

export { MODEL_KEY };

export function fetchCurrentModel(onModel: (name: string) => void): void {
  fetch("/llm/api/model/")
    .then((r) => r.json())
    .then((data) => {
      if (data.success && data.model) onModel(data.model);
    })
    .catch(() => {});
}

export function setModelBadge(
  badge: HTMLElement | null,
  modelName: string,
): void {
  if (!badge) return;
  const display = modelName.includes("/")
    ? modelName.split("/").slice(1).join("/")
    : modelName;
  badge.textContent = display;
  badge.title = modelName;
  sessionStorage.setItem(MODEL_KEY, modelName);
}
