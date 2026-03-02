/**
 * Config Skills — renders App Skills cards in the Agent Sources popover.
 * Extracted from config-mode.ts to keep files under 512 lines.
 */

export interface SkillInfo {
  display_name: string;
  app_name?: string;
  page_patterns?: string[];
  capabilities?: string[];
  tool_prefixes?: string[];
}

export function renderSkills(
  skills: Record<string, SkillInfo>,
  currentPage: string,
  prefs: Record<string, boolean>,
): string {
  const names = Object.keys(skills);
  if (names.length === 0) return "";
  const activeSkill = Object.values(skills).find((s) =>
    s.page_patterns?.some(
      (p) =>
        currentPage.includes(p) || currentPage.startsWith(p.replace(/\/$/, "")),
    ),
  );
  const onCount = names.filter((n) => prefs[n] !== false).length;
  let html = `<div class="ai-config-category" data-cat="App Skills">`;
  html += `<div class="ai-config-category-header">`;
  html += `<i class="fas fa-chevron-right ai-config-category-chevron"></i>`;
  html += `<span class="ai-config-category-name">App Skills</span>`;
  html += `<span class="ai-config-category-count">${onCount}/${names.length}</span>`;
  html += `</div><div class="ai-config-grid">`;
  for (const name of names) {
    const s = skills[name];
    const isActive = (activeSkill as any)?.app_name === name;
    const enabled = prefs[name] !== false;
    const cls = enabled ? "enabled" : "";
    const tag = isActive
      ? ' <span class="ai-config-active-tag">active</span>'
      : "";
    const caps = (s.capabilities?.length ?? 0) + (s.tool_prefixes?.length ?? 0);
    const pages = s.page_patterns?.join(", ") ?? "";
    html += `<div class="ai-config-module ai-config-skill" data-skill="${name}">`;
    html += `<div class="ai-config-card ${cls}">`;
    html += `<i class="fas fa-chevron-right ai-config-module-chevron"></i>`;
    html += `<i class="fas fa-book ai-config-card-icon"></i>`;
    html += `<div class="ai-config-card-info">`;
    html += `<div class="ai-config-card-name">${s.display_name}${tag}</div>`;
    if (pages) html += `<div class="ai-config-card-desc">${pages}</div>`;
    html += `</div>`;
    if (caps) html += `<span class="ai-config-card-badge">${caps}</span>`;
    html += `<label class="ai-config-toggle" onclick="event.stopPropagation()">`;
    html += `<input type="checkbox" ${enabled ? "checked" : ""} />`;
    html += `<span class="ai-config-slider"></span>`;
    html += `</label></div>`;
    html += renderSkillDetails(s);
    html += `</div>`;
  }
  html += `</div></div>`;
  return html;
}

function renderSkillDetails(s: SkillInfo): string {
  const items: string[] = [];
  if (s.capabilities?.length)
    for (const c of s.capabilities)
      items.push(
        `<div class="ai-config-tool-card"><div class="ai-config-tool-desc"><code>${c}</code></div></div>`,
      );
  if (s.tool_prefixes?.length)
    items.push(
      `<div class="ai-config-tool-card"><div class="ai-config-tool-desc">Prefixes: <code>${s.tool_prefixes.join(", ")}</code></div></div>`,
    );
  if (items.length === 0) return "";
  return `<div class="ai-config-tool-cards">${items.join("")}</div>`;
}
