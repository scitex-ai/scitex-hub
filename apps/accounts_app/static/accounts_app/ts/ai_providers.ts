/**
 * AI Providers Settings
 * Loads available providers/models from litellm dynamically,
 * and handles the test-connection flow.
 */

interface ProviderInfo {
  id: string;
  display: string;
  needs_key: boolean;
  models: string[];
}

// Provider API key console URLs
const PROVIDER_KEY_URLS: Record<string, { label: string; url: string }> = {
  anthropic: {
    label: "Get Anthropic key",
    url: "https://console.anthropic.com/settings/keys",
  },
  openai: {
    label: "Get OpenAI key",
    url: "https://platform.openai.com/api-keys",
  },
  gemini: {
    label: "Get Gemini key",
    url: "https://aistudio.google.com/app/apikey",
  },
  mistral: {
    label: "Get Mistral key",
    url: "https://console.mistral.ai/api-keys/",
  },
  xai: { label: "Get xAI key", url: "https://console.x.ai/" },
  deepseek: {
    label: "Get DeepSeek key",
    url: "https://platform.deepseek.com/api_keys",
  },
  openrouter: {
    label: "Get OpenRouter key",
    url: "https://openrouter.ai/settings/keys",
  },
};

// Cache so we only fetch once per page load
let providerCache: ProviderInfo[] | null = null;

async function fetchProviders(): Promise<ProviderInfo[]> {
  if (providerCache) return providerCache;
  const resp = await fetch("/llm/api/providers/available/");
  const data = await resp.json();
  providerCache = data.providers ?? [];
  return providerCache!;
}

function getCsrfToken(): string {
  const el = document.querySelector<HTMLInputElement>(
    'input[name="csrfmiddlewaretoken"]',
  );
  return el?.value ?? "";
}

async function populateProviderSelect(): Promise<void> {
  const select = document.getElementById("service") as HTMLSelectElement | null;
  if (!select) return;

  try {
    const providers = await fetchProviders();
    select.innerHTML = '<option value="">Select a provider...</option>';
    for (const p of providers) {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.display;
      select.appendChild(opt);
    }
  } catch {
    select.innerHTML = '<option value="">Failed to load providers</option>';
  }
}

function updateModelSuggestions(provider: ProviderInfo | undefined): void {
  const datalist = document.getElementById(
    "model-suggestions",
  ) as HTMLDataListElement | null;
  const input = document.getElementById(
    "default_model",
  ) as HTMLInputElement | null;
  if (!datalist || !input) return;

  datalist.innerHTML = "";
  if (!provider) return;

  for (const model of provider.models) {
    const opt = document.createElement("option");
    opt.value = model;
    datalist.appendChild(opt);
  }

  // Pre-fill first model as placeholder hint
  if (provider.models.length > 0) {
    input.placeholder = provider.models[0];
  } else if (provider.id === "ollama") {
    input.placeholder = "e.g., llama3, mistral";
  } else {
    input.placeholder = "Type a model name";
  }
}

function updateApiKeyVisibility(provider: ProviderInfo | undefined): void {
  const group = document.getElementById("api-key-group");
  const linkEl = document.getElementById("api-key-link");
  if (!group) return;

  if (!provider || provider.needs_key) {
    group.style.display = "";
    if (linkEl) {
      const info = provider ? PROVIDER_KEY_URLS[provider.id] : undefined;
      if (info) {
        linkEl.innerHTML = `<a href="${info.url}" target="_blank" rel="noopener">${info.label} →</a>`;
      } else {
        linkEl.innerHTML = "";
      }
    }
  } else {
    // Local provider — no key needed
    group.style.display = "none";
  }
}

async function onProviderChange(): Promise<void> {
  const select = document.getElementById("service") as HTMLSelectElement | null;
  if (!select) return;

  const providers = await fetchProviders();
  const selected = providers.find((p) => p.id === select.value);

  updateModelSuggestions(selected);
  updateApiKeyVisibility(selected);
}

async function testProvider(providerId: string): Promise<void> {
  const btn = document.querySelector<HTMLButtonElement>(
    `[data-provider-id="${providerId}"]`,
  );
  const resultEl = document.getElementById(`test-result-${providerId}`);
  if (!btn || !resultEl) return;

  const originalHTML = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
  btn.disabled = true;
  resultEl.textContent = "";
  resultEl.className = "provider-test-result";

  try {
    const response = await fetch(`/llm/api/providers/${providerId}/test/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });
    const data = await response.json();

    if (data.success) {
      resultEl.textContent = data.message || "Connection OK";
      resultEl.className = "provider-test-result success";
    } else {
      resultEl.textContent = data.error || "Test failed";
      resultEl.className = "provider-test-result error";
    }
  } catch (err) {
    resultEl.textContent = `Network error: ${err}`;
    resultEl.className = "provider-test-result error";
  } finally {
    btn.innerHTML = originalHTML;
    btn.disabled = false;
  }
}

// Track revealed keys per provider id
const revealedKeys: Record<string, string> = {};
const maskedKeys: Record<string, string> = {};

async function toggleRevealKey(providerId: string): Promise<void> {
  const keyEl = document.querySelector<HTMLElement>(
    `.provider-key[data-provider-id="${providerId}"]`,
  );
  const btn = document.querySelector<HTMLButtonElement>(
    `.btn-reveal-key[data-provider-id="${providerId}"]`,
  );
  if (!keyEl || !btn) return;

  const icon = btn.querySelector("i");
  const isRevealed = icon?.classList.contains("fa-eye-slash");

  if (isRevealed) {
    // Hide: restore masked key
    keyEl.textContent = maskedKeys[providerId] ?? keyEl.textContent;
    icon?.classList.replace("fa-eye-slash", "fa-eye");
    return;
  }

  // Reveal: fetch if not yet cached
  if (!revealedKeys[providerId]) {
    maskedKeys[providerId] = keyEl.textContent?.trim() ?? "";
    btn.disabled = true;
    try {
      const resp = await fetch(`/llm/api/providers/${providerId}/key/`);
      const data = await resp.json();
      if (data.success) {
        revealedKeys[providerId] = data.key;
      } else {
        return;
      }
    } finally {
      btn.disabled = false;
    }
  }

  keyEl.textContent = revealedKeys[providerId];
  icon?.classList.replace("fa-eye", "fa-eye-slash");
}

document.addEventListener("DOMContentLoaded", () => {
  // Populate provider dropdown dynamically
  populateProviderSelect();

  // React to provider selection
  document
    .getElementById("service")
    ?.addEventListener("change", onProviderChange);

  // Wire test buttons
  document
    .querySelectorAll<HTMLButtonElement>(".test-provider-btn")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-provider-id");
        if (id) testProvider(id);
      });
    });

  // Wire reveal-key eye buttons
  document
    .querySelectorAll<HTMLButtonElement>(".btn-reveal-key")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-provider-id");
        if (id) toggleRevealKey(id);
      });
    });
});
