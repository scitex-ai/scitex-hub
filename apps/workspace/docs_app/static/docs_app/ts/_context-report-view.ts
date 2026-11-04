/** Local report presentation: text nodes and numeric progress, never HTML input. */
import type { ContextSummary } from "./_context-report";
const format = (value: number) => value.toLocaleString();
export function clearContextReport(root: HTMLElement): void {
  root.querySelector<HTMLElement>("[data-context-output]")!.hidden = true;
  root.querySelector<HTMLElement>("[data-context-owner-rows]")!.replaceChildren();
  root.querySelectorAll<HTMLElement>("[data-context-value]").forEach(field => { field.textContent = ""; });
}
export function renderContextReport(root: HTMLElement, report: ContextSummary): void {
  const values: Record<string, string> = {
    "total-bytes": format(report.total.utf8_bytes), "total-characters": format(report.total.characters),
    "instruction-bytes": format(report.instructions.utf8_bytes), "instruction-raw-bytes": format(report.instructionsRaw.utf8_bytes),
    "instruction-raw-characters": format(report.instructionsRaw.characters), "framing-bytes": format(report.framing.utf8_bytes),
  };
  for (const [name, value] of Object.entries(values)) root.querySelector<HTMLElement>(`[data-context-value="${name}"]`)!.textContent = value;
  const rows = root.querySelector<HTMLElement>("[data-context-owner-rows]")!;
  rows.replaceChildren();
  const maximum = Math.max(1, ...report.owners.map(row => row.size.utf8_bytes));
  for (const row of report.owners) {
    const tr = document.createElement("tr");
    const owner = document.createElement("th"); owner.scope = "row";
    owner.textContent = row.ownership === "unattributed" ? "Unattributed" : row.owner; tr.append(owner);
    for (const value of [row.size.mcp_tools, row.size.skill_headers, row.size.characters, row.size.utf8_bytes]) {
      const cell = document.createElement("td"); cell.textContent = format(value); tr.append(cell);
    }
    const barCell = document.createElement("td"), bar = document.createElement("progress");
    bar.max = maximum; bar.value = row.size.utf8_bytes;
    bar.setAttribute("aria-label", `${owner.textContent}: ${format(row.size.utf8_bytes)} measured UTF-8 bytes, relative to largest owner row`);
    barCell.append(bar); tr.append(barCell); rows.append(tr);
  }
  if (!report.owners.length) {
    const tr = document.createElement("tr"), cell = document.createElement("td"); cell.colSpan = 6;
    cell.textContent = "No tool or skill-header items in this supplied snapshot."; tr.append(cell); rows.append(tr);
  }
  root.querySelector<HTMLElement>("[data-context-output]")!.hidden = false;
}
