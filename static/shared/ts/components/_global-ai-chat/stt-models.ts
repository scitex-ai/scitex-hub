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
  fetch("/llm/api/stt/models/")
    .then((r) => r.json())
    .then((data: SttModelsResponse) => {
      if (!data.available || data.models.length === 0) return;
      const saved = localStorage.getItem(STT_MODEL_KEY);
      select.innerHTML = "";
      for (const m of data.models) {
        const opt = document.createElement("option");
        opt.value = m.name;
        opt.textContent = m.label;
        if (m.name === (saved ?? data.default)) opt.selected = true;
        select.appendChild(opt);
      }
      select.style.display = "";
      select.title = `STT model\n${data.models.map((m) => m.label).join("\n")}`;
      const active = select.value;
      micBtn?.setAttribute("title", `Voice input — model: ${active}`);
      select.addEventListener("change", () => {
        localStorage.setItem(STT_MODEL_KEY, select.value);
        micBtn?.setAttribute("title", `Voice input — model: ${select.value}`);
      });
    })
    .catch(() => {});
}
