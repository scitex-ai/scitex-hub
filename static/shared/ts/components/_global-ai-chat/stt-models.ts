/**
 * STT model selector: fetches available whisper models from the server
 * and populates the <select> element in the AI panel.
 */

const STT_MODEL_KEY = "scitex_stt_model";

interface SttModel {
  name: string;
  label: string;
}

interface SttModelsResponse {
  models: SttModel[];
  default: string | null;
  available: boolean;
}

export function fetchAndPopulateSttModels(
  select: HTMLSelectElement,
  micBtn: HTMLButtonElement | null,
): void {
  fetch("/apps/llm/api/stt/models/")
    .then((r) => r.json())
    .then((data: SttModelsResponse) => {
      if (!data.available || data.models.length === 0) return;
      const saved = localStorage.getItem(STT_MODEL_KEY);
      populateSelect(select, data.models, saved ?? data.default);
      // Keep inline select hidden — settings popover has its own
      const active = select.value;
      micBtn?.setAttribute("title", `Voice input — model: ${active}`);
      select.addEventListener("change", () => {
        localStorage.setItem(STT_MODEL_KEY, select.value);
        micBtn?.setAttribute("title", `Voice input — model: ${select.value}`);
      });
      // Also populate the config popover select and sync
      const configSelect = document.getElementById(
        "scitex-ai-stt-model-config",
      ) as HTMLSelectElement | null;
      if (configSelect) {
        populateSelect(configSelect, data.models, saved ?? data.default);
        configSelect.addEventListener("change", () => {
          select.value = configSelect.value;
          select.dispatchEvent(new Event("change"));
        });
      }
    })
    .catch(() => {});
}

function populateSelect(
  select: HTMLSelectElement,
  models: SttModel[],
  defaultModel: string | null,
): void {
  select.innerHTML = "";
  for (const m of models) {
    const opt = document.createElement("option");
    opt.value = m.name;
    opt.textContent = m.label;
    if (m.name === defaultModel) opt.selected = true;
    select.appendChild(opt);
  }
  select.title = `STT model\n${models.map((m) => m.label).join("\n")}`;
}
