/**
 * Results Renderer for Statistics Calculator
 */

import type { StatsTestConfig } from "./types.ts";

export class ResultsRenderer {
  private container: HTMLElement;

  constructor(selector: string) {
    const elem = document.querySelector(selector);
    if (!elem) {
      throw new Error(`Results container not found: ${selector}`);
    }
    this.container = elem as HTMLElement;
  }

  renderDescriptive(result: Record<string, any>): void {
    const entries = Object.entries(result).map(([key, value]) => {
      const label = this.formatLabel(key);
      const formattedValue = this.formatNumber(value);
      return [label, formattedValue] as [string, string];
    });

    const html = `
      <div class="stats-result">
        <h3>Descriptive Statistics</h3>
        ${this.createResultTable(entries)}
      </div>
    `;
    this.container.innerHTML = html;
  }

  renderTestResult(result: Record<string, any>, config: StatsTestConfig): void {
    const apa = this.formatAPA(result);
    const interpretation = this.createInterpretation(
      result.p_value,
      result.effect_size,
    );
    const suggestions = this.createSuggestions(config.id, result);

    const HIDDEN_KEYS = new Set([
      "formatted",
      "test_method",
      "test",
      "var_x",
      "var_y",
      "alternative",
      "alpha",
      "H0",
      "stat_symbol",
    ]);
    const entries: [string, string][] = [];
    for (const [key, value] of Object.entries(result)) {
      if (HIDDEN_KEYS.has(key)) continue;
      const label = this.formatLabel(key);
      const formatted = this.formatNumber(value);
      entries.push([label, formatted]);
    }

    const html = `
      <div class="stats-result">
        <h3>${config.name} Results</h3>

        <div class="apa-format">
          <div class="apa-header">
            <span class="apa-label">APA Format</span>
            <button class="btn-copy-apa" title="Copy to clipboard">
              <i class="fa-regular fa-copy"></i>
            </button>
          </div>
          <div class="apa-text">${apa || "N/A"}</div>
        </div>

        ${this.createResultTable(entries)}
        ${interpretation}
        ${suggestions}
      </div>
    `;
    this.container.innerHTML = html;
    this.setupCopyButton();
  }

  renderPosthoc(result: Record<string, any>): void {
    const { comparisons, method } = result;

    if (!comparisons || comparisons.length === 0) {
      this.renderError("No pairwise comparisons found in result.");
      return;
    }

    const rows = comparisons
      .map((comp: any) => {
        const sig = comp.p_value < 0.05 ? "significant" : "ns";
        return `
        <tr class="${sig}">
          <td>${comp.group1} vs ${comp.group2}</td>
          <td>${this.formatNumber(comp.statistic)}</td>
          <td>${this.formatNumber(comp.p_value)}</td>
          <td>${comp.p_value < 0.05 ? "✓" : "—"}</td>
        </tr>
      `;
      })
      .join("");

    const html = `
      <div class="stats-result">
        <h3>Post-hoc: ${method || "Unknown Method"}</h3>
        <table class="posthoc-table">
          <thead>
            <tr>
              <th>Comparison</th>
              <th>Statistic</th>
              <th>p-value</th>
              <th>Significant</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
    this.container.innerHTML = html;
  }

  renderEffectSize(result: Record<string, any>): void {
    const { effect_size, measure } = result;
    const effectLabel = this.formatLabel(measure || "effect_size");
    const effectValue = this.formatNumber(effect_size);
    const effectInterpretation = this.interpretEffectSize(measure, effect_size);

    const html = `
      <div class="stats-result">
        <h3>Effect Size</h3>
        <div class="effect-size-display">
          <div class="effect-value">${effectLabel}: ${effectValue}</div>
          <div class="effect-interpretation">${effectInterpretation}</div>
        </div>
      </div>
    `;
    this.container.innerHTML = html;
  }

  renderPower(result: Record<string, any>): void {
    const entries: [string, string][] = [];
    for (const [key, value] of Object.entries(result)) {
      const label = this.formatLabel(key);
      const formatted = this.formatNumber(value);
      entries.push([label, formatted]);
    }

    const html = `
      <div class="stats-result">
        <h3>Power Analysis</h3>
        ${this.createResultTable(entries)}
        <div class="power-note">
          <strong>Note:</strong> Power ≥ 0.80 is typically recommended.
        </div>
      </div>
    `;
    this.container.innerHTML = html;
  }

  renderCorrection(result: Record<string, any>): void {
    const { corrected_pvalues, rejected, method, alpha } = result;

    if (!corrected_pvalues || corrected_pvalues.length === 0) {
      this.renderError("No corrected p-values found.");
      return;
    }

    const rows = corrected_pvalues
      .map((p: number, idx: number) => {
        const isRejected = rejected && rejected[idx];
        const sigClass = isRejected ? "significant" : "ns";
        return `
        <tr class="${sigClass}">
          <td>Test ${idx + 1}</td>
          <td>${this.formatNumber(p)}</td>
          <td>${isRejected ? "✓" : "—"}</td>
        </tr>
      `;
      })
      .join("");

    const html = `
      <div class="stats-result">
        <h3>Correction: ${method || "Unknown"} (α=${alpha || 0.05})</h3>
        <table class="correction-table">
          <thead>
            <tr>
              <th>Test</th>
              <th>Corrected p-value</th>
              <th>Reject H₀</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
    this.container.innerHTML = html;
  }

  renderRecommendations(recommendations: string[]): void {
    if (!recommendations || recommendations.length === 0) {
      this.renderError("No recommendations available.");
      return;
    }

    const items = recommendations.map((rec) => `<li>${rec}</li>`).join("");
    const html = `
      <div class="stats-result">
        <h3>Recommended Tests</h3>
        <ul class="recommendations-list">${items}</ul>
      </div>
    `;
    this.container.innerHTML = html;
  }

  renderError(message: string): void {
    const html = `
      <div class="stats-error">
        <strong>Error:</strong> ${message}
      </div>
    `;
    this.container.innerHTML = html;
  }

  private createResultTable(entries: [string, string][]): string {
    const rows = entries
      .map(([label, value]) => `<tr><td>${label}</td><td>${value}</td></tr>`)
      .join("");
    return `
      <table class="result-table">
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  private formatAPA(result: Record<string, any>): string {
    if (result.formatted) {
      return result.formatted;
    }
    // Fallback: construct simple APA format
    const { statistic, p_value, df, stat_symbol } = result;
    const sym = stat_symbol || "stat";
    if (statistic !== undefined && p_value !== undefined) {
      const statStr = this.formatNumber(statistic);
      const pStr = this.formatNumber(p_value);
      if (df !== undefined) {
        return `${sym}(${df}) = ${statStr}, p = ${pStr}`;
      }
      return `${sym} = ${statStr}, p = ${pStr}`;
    }
    return "";
  }

  private createInterpretation(pValue?: number, effectSize?: number): string {
    if (pValue === undefined) return "";

    const significant = pValue < 0.05;
    const barClass = significant ? "sig-bar-significant" : "sig-bar-ns";
    const sigText = significant
      ? "Significant (p < 0.05)"
      : "Not Significant (p ≥ 0.05)";

    return `
      <div class="interpretation">
        <div class="sig-bar ${barClass}">${sigText}</div>
      </div>
    `;
  }

  private createSuggestions(
    testId: string,
    result: Record<string, any>,
  ): string {
    const suggestions: string[] = [];

    if (testId === "anova" && result.p_value && result.p_value < 0.05) {
      suggestions.push(
        "ANOVA is significant. Consider running Tukey HSD or Games-Howell post-hoc test.",
      );
    }
    if (testId === "kruskal" && result.p_value && result.p_value < 0.05) {
      suggestions.push(
        "Kruskal-Wallis is significant. Consider running pairwise Mann-Whitney tests with correction.",
      );
    }
    if (
      ["ttest_ind", "ttest_paired"].includes(testId) &&
      result.p_value &&
      result.p_value < 0.05
    ) {
      suggestions.push(
        "Significant difference found. Calculate Cohen's d for effect size.",
      );
    }

    if (suggestions.length === 0) return "";

    const items = suggestions.map((s) => `<li>${s}</li>`).join("");
    return `
      <div class="suggestions">
        <strong>Suggestions:</strong>
        <ul>${items}</ul>
      </div>
    `;
  }

  private interpretEffectSize(
    measure: string | undefined,
    value: number,
  ): string {
    if (value === undefined || value === null) return "";

    if (measure === "cohens_d") {
      const abs = Math.abs(value);
      if (abs < 0.2) return "Negligible effect";
      if (abs < 0.5) return "Small effect";
      if (abs < 0.8) return "Medium effect";
      return "Large effect";
    }

    if (measure === "cliffs_delta") {
      const abs = Math.abs(value);
      if (abs < 0.147) return "Negligible";
      if (abs < 0.33) return "Small";
      if (abs < 0.474) return "Medium";
      return "Large";
    }

    return "";
  }

  private formatLabel(key: string): string {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  private formatNumber(value: any): string {
    if (typeof value === "number") {
      if (Number.isInteger(value)) return value.toString();
      if (Math.abs(value) < 0.001) return value.toExponential(3);
      return value.toFixed(4);
    }
    return String(value);
  }

  private setupCopyButton(): void {
    const btn = this.container.querySelector(
      ".btn-copy-apa",
    ) as HTMLButtonElement;
    if (!btn) return;

    btn.addEventListener("click", () => {
      const el = this.container.querySelector(".apa-text");
      if (!el) return;

      const text = el.textContent || "";
      navigator.clipboard
        .writeText(text)
        .then(() => {
          const icon = btn.querySelector("i");
          if (icon) {
            icon.className = "fa-solid fa-check";
            setTimeout(() => {
              icon.className = "fa-regular fa-copy";
            }, 2000);
          }
        })
        .catch((err) => {
          console.error("Failed to copy:", err);
        });
    });
  }
}
