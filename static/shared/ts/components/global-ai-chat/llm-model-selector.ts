/**
 * LLM model selector: fetches user's configured providers and populates
 * the model dropdown in the AI panel settings.
 */

const LLM_MODEL_KEY = "scitex_llm_model";

interface Provider {
  id: number;
  name: string;
  provider_type: string;
  model_name: string;
  is_default: boolean;
}

export function fetchAndPopulateLlmModels(
  select: HTMLSelectElement,
  badgeEl: HTMLElement | null,
): void {
  fetch("/llm/api/providers/")
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
        const opt = document.createElement("option");
        opt.value = p.model_name;
        opt.textContent = `${p.model_name} (${p.provider_type})`;
        if (p.model_name === saved || (!saved && p.is_default)) {
          opt.selected = true;
        }
        select.appendChild(opt);
      }

      if (badgeEl && select.value) {
        const display = select.value.includes("/")
          ? select.value.split("/").pop()!
          : select.value;
        badgeEl.textContent = display;
        badgeEl.title = select.value;
      }

      select.addEventListener("change", () => {
        localStorage.setItem(LLM_MODEL_KEY, select.value);
        if (badgeEl) {
          const display = select.value.includes("/")
            ? select.value.split("/").pop()!
            : select.value;
          badgeEl.textContent = display;
          badgeEl.title = select.value;
        }
      });
    })
    .catch(() => {});
}
