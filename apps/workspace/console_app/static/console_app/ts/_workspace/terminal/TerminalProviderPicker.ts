/**
 * Terminal model-provider picker (Option A model-agnostic sessions).
 *
 * A small <select> rendered in the terminal tab bar. The selection
 * applies to NEWLY created terminal sessions (env cannot change on a
 * live PTY). Provider ids are validated server-side; API keys are
 * resolved server-side from the user's stored keys — this control only
 * ever sends an identifier.
 */

export interface TerminalProviderInfo {
  id: string;
  label: string;
  requires_key: boolean;
  has_key: boolean;
}

interface ProvidersResponse {
  success: boolean;
  default: string;
  picker_enabled: boolean;
  picker_disabled_reason: string;
  key_settings_url: string;
  providers: TerminalProviderInfo[];
}

const STORAGE_KEY = "scitex-terminal-provider";

export class TerminalProviderPicker {
  private data: ProvidersResponse | null = null;
  private selectEl: HTMLSelectElement | null = null;

  /** Load the server-side registry. Fail-loud: on error the picker is
   *  simply not rendered (sessions then use the server default). */
  async load(): Promise<void> {
    try {
      const resp = await fetch("/apps/console/api/terminal/providers/");
      if (!resp.ok) {
        console.error(
          `[ProviderPicker] registry fetch failed: HTTP ${resp.status}`,
        );
        return;
      }
      this.data = (await resp.json()) as ProvidersResponse;
    } catch (err) {
      console.error("[ProviderPicker] registry fetch failed:", err);
    }
  }

  /** Provider id to use for a NEW terminal session ("" = server default). */
  getSelectedProvider(): string {
    if (!this.data?.picker_enabled) return "";
    const value =
      this.selectEl?.value ?? sessionStorage.getItem(STORAGE_KEY) ?? "";
    return value === this.data.default ? "" : value;
  }

  /** Render the picker into the tab bar (idempotent per container). */
  render(container: HTMLElement): void {
    if (!this.data) return;
    container.querySelector(".terminal-provider-picker")?.remove();

    const select = document.createElement("select");
    select.className = "terminal-provider-picker";
    select.style.cssText =
      "max-width: 150px; font-size: 11px; margin-left: 4px;" +
      "background: var(--workspace-bg-primary); color: var(--text-primary);" +
      "border: 1px solid var(--workspace-border, #444); border-radius: 3px;";

    for (const provider of this.data.providers) {
      const option = document.createElement("option");
      option.value = provider.id;
      option.textContent =
        provider.requires_key && !provider.has_key
          ? `${provider.label} — add key in AI Setup`
          : provider.label;
      select.appendChild(option);
    }

    const saved = sessionStorage.getItem(STORAGE_KEY);
    select.value =
      saved && this.data.providers.some((p) => p.id === saved)
        ? saved
        : this.data.default;

    if (this.data.picker_enabled) {
      select.title =
        "Model provider for NEW terminal sessions. API-key providers " +
        `use your own key from AI Setup (${this.data.key_settings_url}).`;
    } else {
      // Standard fail-loud explanation (e.g. readonly visitor).
      select.disabled = true;
      select.title = this.data.picker_disabled_reason;
    }

    select.onchange = () => {
      try {
        sessionStorage.setItem(STORAGE_KEY, select.value);
      } catch {
        /* sessionStorage unavailable */
      }
    };

    this.selectEl = select;
    container.appendChild(select);
  }
}
