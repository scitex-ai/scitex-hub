/**
 * Config Mode — MCP Tool Toggles, Skills, Page Hints
 * Renders interactive toggle cards in the AI panel Config tab.
 */

import type { AIPanelChatMode } from "./chat-mode";
import { renderSkills } from "./config-skills";
import type { SkillInfo } from "./config-skills";
import { readActiveProjectSlug } from "./context";
import { API_URLS } from "../../utils/api-urls";

interface McpToolParam {
  name: string;
  type: string;
  default: string;
}

interface McpTool {
  name: string;
  desc: string;
  params: McpToolParam[];
  returns: string;
}

interface McpModule {
  category: string;
  icon: string;
  prefix: string;
  count: number;
  tools: McpTool[];
}

interface McpPrefsGroup {
  name: string;
  display: string;
  icon: string;
  desc: string;
  enabled: boolean;
  tool_count: number;
  tools: string[];
}

interface McpPrefsCategory {
  name: string;
  groups: McpPrefsGroup[];
}

export class AIPanelConfigMode {
  private saveTimer: ReturnType<typeof setTimeout> | null = null;

  private static prefsKey(base: string): string {
    const slug = readActiveProjectSlug();
    return slug ? `${base}-${slug}` : base;
  }

  private loadLocalPrefs(key: string): Record<string, boolean> {
    try {
      return JSON.parse(localStorage.getItem(key) || "{}");
    } catch {
      return {};
    }
  }

  private saveLocalPrefs(key: string, prefs: Record<string, boolean>): void {
    localStorage.setItem(key, JSON.stringify(prefs));
  }

  async populate(
    container: HTMLElement,
    chatMode: AIPanelChatMode | null,
  ): Promise<void> {
    try {
      const [mcpPrefs, toolsCatalog, skillsResp, pageHints] = await Promise.all(
        [
          fetch("/accounts/api/mcp-preferences/").then((r) => r.json()),
          fetch("/api/mcp/tools/").then((r) => r.json()),
          fetch("/apps/llm/api/skills/").then((r) => r.json()),
          Promise.resolve(chatMode?.collectPageHints() ?? []),
        ],
      );

      const enabledMap: Record<string, boolean> = {};
      for (const cat of (mcpPrefs.categories || []) as McpPrefsCategory[]) {
        for (const g of cat.groups) {
          enabledMap[g.name] = g.enabled;
        }
      }

      const modules: McpModule[] = toolsCatalog.modules || [];
      const skills: Record<string, SkillInfo> = skillsResp.skills || {};
      const currentPage = window.location.pathname;
      const skillPrefs = this.loadLocalPrefs(
        AIPanelConfigMode.prefsKey("stx-shell-ai-skill-prefs"),
      );
      const hintPrefs = this.loadLocalPrefs(
        AIPanelConfigMode.prefsKey("stx-shell-ai-hint-prefs"),
      );

      let html = "";
      html += renderSkills(skills, currentPage, skillPrefs);
      html += this.renderPageHints(hintPrefs);
      html += this.renderMcpTools(modules, enabledMap, toolsCatalog.total || 0);
      html += this.renderContextPreview();

      container.innerHTML = html;

      this.bindCategoryHeaders(container);
      this.bindModuleExpand(container);
      this.bindMcpToggles(container);
      this.bindSkillToggles(container);
      this.bindHintToggles(container);
      container
        .querySelector(".ai-context-download-btn")
        ?.addEventListener("click", () =>
          this.downloadContext(pageHints, currentPage),
        );
    } catch {
      container.innerHTML =
        '<div class="ai-config-hint-item">Failed to load config</div>';
    }
  }

  /* ── Renderers ───────────────────────────────────────── */

  private renderPageHints(prefs: Record<string, boolean>): string {
    const hintEls = document.querySelectorAll<HTMLElement>("[data-ai-hint]");
    if (hintEls.length === 0) return "";
    const onCount = Array.from(hintEls).filter(
      (_, i) => prefs[`hint_${i}`] !== false,
    ).length;
    let html = `<div class="ai-config-category" data-cat="Page Context">`;
    html += `<div class="ai-config-category-header">`;
    html += `<i class="fas fa-chevron-right ai-config-category-chevron"></i>`;
    html += `<span class="ai-config-category-name">Page Context</span>`;
    html += `<span class="ai-config-category-count">${onCount}/${hintEls.length} → page_hints[]</span>`;
    html += `</div><div class="ai-config-grid">`;
    hintEls.forEach((el, i) => {
      const hint = el.dataset.aiHint || "";
      const safe = hint
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      const enabled = prefs[`hint_${i}`] !== false;
      const cls = enabled ? "enabled" : "";
      const tag = el.tagName.toLowerCase();
      const elId = el.id ? `#${el.id}` : "";
      const elCls = el.className
        ? `.${el.className.trim().split(/\s+/).join(".")}`
        : "";
      html += `<label class="ai-config-card ai-config-hint ${cls}" data-hint="hint_${i}">`;
      html += `<i class="fas fa-lightbulb ai-config-card-icon"></i>`;
      html += `<div class="ai-config-card-info">`;
      html += `<div class="ai-config-card-name">${safe}</div>`;
      html += `<div class="ai-config-card-desc"><code>&lt;${tag}${elId}${elCls}&gt;</code></div>`;
      html += `</div>`;
      html += `<div class="ai-config-toggle">`;
      html += `<input type="checkbox" ${enabled ? "checked" : ""} />`;
      html += `<span class="ai-config-slider"></span>`;
      html += `</div></label>`;
    });
    html += `</div></div>`;
    return html;
  }

  private renderMcpTools(
    modules: McpModule[],
    enabledMap: Record<string, boolean>,
    total: number,
  ): string {
    const onCount = modules.filter((m) => {
      const key = m.prefix.replace(/_$/, "").toUpperCase();
      return enabledMap[key] !== false;
    }).length;
    let html = `<div class="ai-config-category" data-cat="MCP Tools">`;
    html += `<div class="ai-config-category-header">`;
    html += `<i class="fas fa-chevron-right ai-config-category-chevron"></i>`;
    html += `<span class="ai-config-category-name">MCP Tools</span>`;
    html += `<span class="ai-config-category-count">SciTeX · ${total} tools / ${onCount}/${modules.length} groups</span>`;
    html += `</div><div class="ai-config-grid">`;
    for (const m of modules) {
      html += this.renderModuleCard(m, enabledMap);
    }
    html += `</div></div>`;
    return html;
  }

  private renderModuleCard(
    m: McpModule,
    enabledMap: Record<string, boolean>,
  ): string {
    const groupKey = m.prefix.replace(/_$/, "").toUpperCase();
    const enabled = enabledMap[groupKey] !== false;
    const cls = enabled ? "enabled" : "";
    let html = `<div class="ai-config-module" data-group="${groupKey}">`;
    html += `<div class="ai-config-card ${cls}">`;
    html += `<i class="fas fa-chevron-right ai-config-module-chevron"></i>`;
    html += `<i class="fas ${m.icon} ai-config-card-icon"></i>`;
    html += `<div class="ai-config-card-info">`;
    html += `<div class="ai-config-card-name">${m.category}</div>`;
    html += `<div class="ai-config-card-desc">${m.prefix}* (${m.count} tools)</div>`;
    html += `</div>`;
    html += `<span class="ai-config-card-badge">${m.count}</span>`;
    html += `<label class="ai-config-toggle" onclick="event.stopPropagation()">`;
    html += `<input type="checkbox" ${enabled ? "checked" : ""} />`;
    html += `<span class="ai-config-slider"></span>`;
    html += `</label></div>`;
    if (m.tools.length > 0) {
      html += `<div class="ai-config-tool-cards">`;
      for (const t of m.tools) {
        html += `<div class="ai-config-tool-card">`;
        html += `<div class="ai-config-tool-name"><code>${t.name}</code>`;
        html += ` <span class="ai-config-tool-returns">→ ${t.returns}</span></div>`;
        html += `<div class="ai-config-tool-desc">${t.desc}</div>`;
        if (t.params.length > 0) {
          html += `<div class="ai-config-tool-params">`;
          for (const p of t.params) {
            const def =
              p.default === "required"
                ? '<span class="ai-config-param-req">required</span>'
                : `<span class="ai-config-param-def">= ${p.default}</span>`;
            html += `<span class="ai-config-param">`;
            html += `<code>${p.name}</code>: <em>${p.type}</em> ${def}`;
            html += `</span>`;
          }
          html += `</div>`;
        }
        html += `</div>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
    return html;
  }

  private renderContextPreview(): string {
    const page = window.location.href;
    let html = `<div class="ai-config-context-preview">`;
    html += `<div class="ai-config-tool-name"><code>Agent Context</code>`;
    html += ` <span class="ai-config-tool-returns">→ POST ${API_URLS.llm.chatStream}</span></div>`;
    html += `<div class="ai-config-tool-desc">`;
    html += `<code>page</code>: ${page}<br>`;
    html += `<code>project_slug</code>: active project<br>`;
    html += `<code>page_hints[]</code>: enabled hints above</div></div>`;
    html += `<button class="ai-context-download-btn" title="Download full agent context as JSON">`;
    html += `<i class="fas fa-download"></i> Download Agent Context</button>`;
    return html;
  }

  /* ── Interaction Bindings ────────────────────────────── */

  private bindCategoryHeaders(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-category-header")
      .forEach((header) => {
        header.addEventListener("click", () => {
          header.closest(".ai-config-category")?.classList.toggle("expanded");
        });
      });
  }

  private bindModuleExpand(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-module > .ai-config-card")
      .forEach((card) => {
        card.style.cursor = "pointer";
        card.addEventListener("click", (e) => {
          if ((e.target as HTMLElement).closest(".ai-config-toggle")) return;
          card.closest(".ai-config-module")?.classList.toggle("expanded");
        });
      });
  }

  private updateCount(el: HTMLElement, sel: string, suffix = ""): void {
    const cat = el.closest(".ai-config-category");
    if (!cat) return;
    const total = cat.querySelectorAll(sel).length;
    const on = cat.querySelectorAll(`${sel}.enabled`).length;
    const badge = cat.querySelector(".ai-config-category-count");
    if (badge) badge.textContent = `${on}/${total}${suffix}`;
  }

  private bindMcpToggles(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-module")
      .forEach((mod) => {
        const cb = mod.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (!cb) return;
        cb.addEventListener("change", () => {
          mod
            .querySelector(".ai-config-card")
            ?.classList.toggle("enabled", cb.checked);
          const cat = mod.closest(".ai-config-category");
          if (cat) {
            const total = cat.querySelectorAll(".ai-config-module").length;
            const on = cat.querySelectorAll(
              ".ai-config-module .ai-config-card.enabled",
            ).length;
            const badge = cat.querySelector(".ai-config-category-count");
            if (badge) badge.textContent = `SciTeX · ${on}/${total} groups`;
          }
          this.debouncedSaveMcp(container);
        });
      });
  }

  private bindSkillToggles(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-skill")
      .forEach((mod) => {
        const cb = mod.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (!cb) return;
        cb.addEventListener("change", () => {
          mod
            .querySelector(".ai-config-card")
            ?.classList.toggle("enabled", cb.checked);
          const cat = mod.closest(".ai-config-category");
          if (cat) {
            const on = cat.querySelectorAll(
              ".ai-config-skill .ai-config-card.enabled",
            ).length;
            const total = cat.querySelectorAll(".ai-config-skill").length;
            const badge = cat.querySelector(".ai-config-category-count");
            if (badge) badge.textContent = `${on}/${total}`;
          }
          this.saveSkillPrefs(container);
          this.showToast();
        });
      });
  }

  private bindHintToggles(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-hint")
      .forEach((card) => {
        const cb = card.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (!cb) return;
        cb.addEventListener("change", () => {
          card.classList.toggle("enabled", cb.checked);
          this.updateCount(card, ".ai-config-hint", " → page_hints[]");
          this.saveHintPrefs(container);
          this.showToast();
        });
      });
  }

  private saveSkillPrefs(container: HTMLElement): void {
    const prefs: Record<string, boolean> = {};
    container
      .querySelectorAll<HTMLElement>(".ai-config-skill")
      .forEach((card) => {
        const name = card.getAttribute("data-skill");
        const cb = card.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (name && cb) prefs[name] = cb.checked;
      });
    this.saveLocalPrefs(
      AIPanelConfigMode.prefsKey("stx-shell-ai-skill-prefs"),
      prefs,
    );
  }

  private saveHintPrefs(container: HTMLElement): void {
    const prefs: Record<string, boolean> = {};
    container
      .querySelectorAll<HTMLElement>(".ai-config-hint")
      .forEach((card) => {
        const key = card.getAttribute("data-hint");
        const cb = card.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (key && cb) prefs[key] = cb.checked;
      });
    this.saveLocalPrefs(
      AIPanelConfigMode.prefsKey("stx-shell-ai-hint-prefs"),
      prefs,
    );
  }

  /* ── Debounced Save ──────────────────────────────────── */

  private debouncedSaveMcp(container: HTMLElement): void {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(async () => {
      const prefs: Record<string, boolean> = {};
      container
        .querySelectorAll<HTMLElement>(".ai-config-module")
        .forEach((mod) => {
          const name = mod.getAttribute("data-group");
          const cb = mod.querySelector<HTMLInputElement>(
            'input[type="checkbox"]',
          );
          if (name && cb) prefs[name] = cb.checked;
        });
      const csrf =
        document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
          ?.value ??
        (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
      try {
        const resp = await fetch("/accounts/api/mcp-preferences/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
          },
          body: JSON.stringify(prefs),
        });
        if (resp.ok) this.showToast();
      } catch {
        console.error("[AI Config] Failed to save MCP preferences");
      }
    }, 500);
  }

  private showToast(): void {
    const toast = document.getElementById("ai-config-toast");
    if (!toast) return;
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 1500);
  }

  /* ── Download Agent Context ──────────────────────────── */

  private async downloadContext(
    pageHints: string[],
    page: string,
  ): Promise<void> {
    try {
      const csrf =
        document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
          ?.value ??
        (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
      const resp = await fetch("/apps/llm/api/agent-context/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
        },
        body: JSON.stringify({ page, page_hints: pageHints }),
      });
      const data = await resp.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agent-context-${new Date().toISOString().slice(0, 19).replace(/:/g, "")}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      console.error("[AI] Failed to download agent context");
    }
  }
}
