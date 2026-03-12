/**
 * EditableDefaultsBuilder - Builds editable defaults UI
 *
 * Responsibilities:
 * - Generate HTML for editable style defaults
 * - Handle input formatting and unit conversion display
 */

export interface EditableDefaultsCallbacks {
  formatKey: (key: string) => string;
  formatWithUnit: (value: number, isSizeValue: boolean) => string;
  getCurrentUnit: () => "mm" | "inch";
  onValueChange: (key: string, value: any, isSize: boolean) => void;
  onNavigate: (direction: "up" | "down", currentIndex: number) => void;
}

interface SectionConfig {
  keys: string[];
  isSize: boolean;
  labels?: Record<string, string>;
}

const SECTIONS: Record<string, SectionConfig> = {
  "Labels (live preview)": {
    keys: ["title", "xlabel", "ylabel"],
    isSize: false,
    labels: {
      title: "Title",
      xlabel: "X-axis Label",
      ylabel: "Y-axis Label",
    },
  },
  "Axes Dimensions": {
    keys: ["axes_width_mm", "axes_height_mm", "axes_thickness_mm"],
    isSize: true,
  },
  Margins: {
    keys: [
      "margin_left_mm",
      "margin_right_mm",
      "margin_bottom_mm",
      "margin_top_mm",
    ],
    isSize: true,
  },
  "Font Sizes (pt)": {
    keys: [
      "axis_font_size_pt",
      "tick_font_size_pt",
      "title_font_size_pt",
      "legend_font_size_pt",
    ],
    isSize: false,
  },
  Lines: {
    keys: ["trace_thickness_mm", "tick_length_mm", "tick_thickness_mm", "n_ticks"],
    isSize: true,
  },
  Output: {
    keys: ["dpi", "transparent", "auto_crop", "font_family"],
    isSize: false,
  },
};

export class EditableDefaultsBuilder {
  /**
   * Build editable defaults HTML
   */
  public static buildHTML(
    defaults: Record<string, any>,
    callbacks: EditableDefaultsCallbacks,
  ): string {
    const currentUnit = callbacks.getCurrentUnit();
    let html = '<div class="defaults-list">';

    for (const [sectionTitle, config] of Object.entries(SECTIONS)) {
      html += `<div class="defaults-section">
                <div class="defaults-section-title">${sectionTitle}</div>
                <table class="defaults-table">`;

      for (const key of config.keys) {
        if (key in defaults) {
          const value = defaults[key];
          const displayLabel = config.labels?.[key] || callbacks.formatKey(key);
          const isSizeValue = config.isSize && typeof value === "number";
          const displayValue = isSizeValue
            ? callbacks.formatWithUnit(value, true)
            : value;
          const isBoolean = typeof value === "boolean";

          html += EditableDefaultsBuilder.buildRowHTML(
            key,
            displayLabel,
            displayValue,
            isBoolean,
            isSizeValue,
            value,
            currentUnit,
          );
        }
      }
      html += `</table></div>`;
    }

    html += "</div>";
    return html;
  }

  private static buildRowHTML(
    key: string,
    displayLabel: string,
    displayValue: any,
    isBoolean: boolean,
    isSizeValue: boolean,
    value: any,
    currentUnit: string,
  ): string {
    if (isBoolean) {
      return `
                <tr class="defaults-row">
                    <td class="defaults-label" title="${displayLabel}">${displayLabel}</td>
                    <td class="defaults-value" colspan="2">
                        <label class="checkbox-label">
                            <input type="checkbox"
                                   class="preset-input"
                                   data-key="${key}"
                                   ${value ? "checked" : ""}>
                            <span>${value ? "ON" : "OFF"}</span>
                        </label>
                    </td>
                </tr>`;
    }

    return `
            <tr class="defaults-row">
                <td class="defaults-label" title="${displayLabel}">${displayLabel}</td>
                <td class="defaults-value">
                    <input type="text"
                           class="preset-input"
                           data-key="${key}"
                           data-is-size="${isSizeValue}"
                           value="${displayValue}"
                           title="${key}: ${displayValue}">
                </td>
                <td class="defaults-unit">${isSizeValue ? currentUnit : ""}</td>
            </tr>`;
  }

  /**
   * Setup event listeners for editable defaults inputs
   */
  public static setupListeners(
    container: HTMLElement,
    callbacks: EditableDefaultsCallbacks,
  ): void {
    const inputs = Array.from(
      container.querySelectorAll(".preset-input"),
    ) as HTMLInputElement[];

    inputs.forEach((input, index) => {
      input.addEventListener("change", (e) => {
        const target = e.target as HTMLInputElement;
        const key = target.getAttribute("data-key");
        if (!key) return;

        if (target.type === "checkbox") {
          callbacks.onValueChange(key, target.checked, false);
          const span = target.nextElementSibling;
          if (span) span.textContent = target.checked ? "ON" : "OFF";
        } else {
          const isSize = target.getAttribute("data-is-size") === "true";
          callbacks.onValueChange(key, target.value, isSize);
        }
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          const nextIndex = (index + 1) % inputs.length;
          inputs[nextIndex].focus();
          inputs[nextIndex].select();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          const prevIndex = (index - 1 + inputs.length) % inputs.length;
          inputs[prevIndex].focus();
          inputs[prevIndex].select();
        }
      });
    });
  }
}
