/**
 * LLM model selector: fetches user's configured providers and populates
 * the model dropdown in the AI panel settings.
 */

import { API_URLS } from "../../utils/api-urls";

const LLM_MODEL_KEY = "scitex_llm_model";

interface Provider {
  id: number;
  service: string;
  service_display: string;
  default_model: string;
}

export function fetchAndPopulateLlmModels(
  select: HTMLSelectElement,
  badgeEl: HTMLElement | null,
): void {
  fetch(API_URLS.llm.providers)
    .then((r) => r.json())
    .then((data: { providers: Provider[] }) => {
      if (!data.providers || data.providers.length === 0) {
        const opt = document.createElement("option");
        opt.textContent = "No providers configured";
        opt.disabled = true;
        select.appendChild(opt);
        return;
      }

      const saved = localStorage.getItem(LLM_MODEL_KEY);
      select.innerHTML = "";
      for (const p of data.providers) {
        const model = p.default_model || p.service;
        const opt = document.createElement("option");
        opt.value = model;
        opt.textContent = `${model} (${p.service_display})`;
        if (model === saved || (!saved && data.providers.indexOf(p) === 0)) {
          opt.selected = true;
        }
        select.appendChild(opt);
      }

      const configBadge = document.getElementById(
        "stx-shell-ai-config-model-badge",
      );
      const updateBadges = () => {
        const val = select.value;
        const display = val.includes("/") ? val.split("/").pop()! : val;
        if (badgeEl) {
          badgeEl.textContent = display;
          badgeEl.title = val;
        }
        if (configBadge) {
          configBadge.textContent = display;
          configBadge.title = val;
        }
      };
      if (select.value) updateBadges();

      select.addEventListener("change", () => {
        localStorage.setItem(LLM_MODEL_KEY, select.value);
        updateBadges();
      });
    })
    .catch(() => {});
}
