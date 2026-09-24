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
      if (!data.providers || data.providers.length === 0) {
        // No BYOK providers: fall back to the funded model (if any) so the
        // badge switcher never opens an empty menu. Selecting it keeps the
        // default funded path.
        fetch(API_URLS.llm.model)
          .then((r) => r.json())
          .then(
            (m: {
              success: boolean;
              model?: string;
              display?: string;
              funded?: boolean;
            }) => {
              select.innerHTML = "";
              const opt = document.createElement("option");
              if (m.success && m.model) {
                opt.value = m.model;
                const short = m.model.includes("/")
                  ? m.model.split("/").pop()!
                  : m.model;
                opt.textContent = m.funded
                  ? `${short} (SciTeX Free)`
                  : `${short}`;
                opt.selected = true;
              } else {
                opt.textContent = "No providers configured";
                opt.disabled = true;
              }
              select.appendChild(opt);
              if (select.value) updateBadges();
            },
          )
          .catch(() => {
            select.innerHTML = "";
            const opt = document.createElement("option");
            opt.textContent = "No providers configured";
            opt.disabled = true;
            select.appendChild(opt);
          });
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

      if (select.value) updateBadges();

      select.addEventListener("change", () => {
        localStorage.setItem(LLM_MODEL_KEY, select.value);
        updateBadges();
      });
    })
    .catch((err) => {
      console.error("[llm-model-selector] Failed to fetch providers:", err);
      const opt = document.createElement("option");
      opt.textContent = "Failed to load models";
      opt.disabled = true;
      select.appendChild(opt);
    });
}
