/**
 * Config Limits — Daily Limits section for AI panel Config tab.
 * Renders limit inputs and handles debounced save to /accounts/api/ai-limits/.
 */

/** Get CSRF token from cookie or hidden form field. */
function getCsrf(): string {
  return (
    document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
      ?.value ??
    (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "")
  );
}

/** Render the Daily Limits section HTML. */
export function renderLimits(resp: any): string {
  if (!resp.configured) {
    const url = resp.configure_url || "/accounts/settings/ai-providers/";
    return (
      `<div class="ai-config-category" data-cat="Daily Limits">` +
      `<div class="ai-config-category-header">` +
      `<i class="fas fa-chevron-right ai-config-category-chevron"></i>` +
      `<span class="ai-config-category-name">Daily Limits</span>` +
      `</div><div class="ai-config-grid">` +
      `<div class="ai-config-limits-unconfigured">` +
      `<i class="fas fa-cog"></i> No AI provider configured. ` +
      `<a href="${url}">Set up provider</a></div>` +
      `</div></div>`
    );
  }
  const lim = resp.limits || {};
  const fmt = (v: any) => (v === null || v === undefined ? "" : String(v));
  const fields: [string, string][] = [
    ["daily_request_limit", "Request limit"],
    ["daily_token_limit", "Token limit"],
    ["daily_cost_limit_usd", "Cost limit (USD)"],
  ];
  let html = `<div class="ai-config-category" data-cat="Daily Limits">`;
  html += `<div class="ai-config-category-header">`;
  html += `<i class="fas fa-chevron-right ai-config-category-chevron"></i>`;
  html += `<span class="ai-config-category-name">Daily Limits</span>`;
  html += `<span class="ai-config-category-count">`;
  html += `<a href="/accounts/settings/ai-providers/" class="ai-config-settings-link" title="Full settings"><i class="fas fa-external-link-alt"></i></a>`;
  html += `</span>`;
  html += `</div><div class="ai-config-grid">`;
  html += `<div class="ai-config-limits-form">`;
  for (const [key, label] of fields) {
    const val = fmt(lim[key]);
    const placeholder = "\u221e (unlimited)";
    const step = key === "daily_cost_limit_usd" ? "0.01" : "1";
    html += `<label class="ai-config-limit-row">`;
    html += `<span class="ai-config-limit-label">${label}</span>`;
    html += `<input type="number" class="ai-config-limit-input" `;
    html += `data-limit="${key}" value="${val}" placeholder="${placeholder}" `;
    html += `min="0" step="${step}" />`;
    html += `</label>`;
  }
  html += `</div></div></div>`;
  return html;
}

/** Bind limit inputs with debounced auto-save. */
export function bindLimitsInputs(
  container: HTMLElement,
  showToast: () => void,
): void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  container
    .querySelectorAll<HTMLInputElement>(".ai-config-limit-input")
    .forEach((input) => {
      input.addEventListener("input", () => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(async () => {
          const data: Record<string, any> = {};
          container
            .querySelectorAll<HTMLInputElement>(".ai-config-limit-input")
            .forEach((inp) => {
              const key = inp.dataset.limit;
              if (key) data[key] = inp.value === "" ? null : inp.value;
            });
          try {
            const resp = await fetch("/accounts/api/ai-limits/", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrf(),
              },
              body: JSON.stringify(data),
            });
            if (resp.ok) showToast();
          } catch {
            console.error("[AI Config] Failed to save limits");
          }
        }, 800);
      });
    });
}
