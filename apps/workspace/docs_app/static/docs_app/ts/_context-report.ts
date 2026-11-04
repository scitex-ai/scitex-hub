/** Validate a finite Dev report without accepting tool bodies or executing input. */
export const REPORT_SCHEMA = "scitex-context-report/1";
export const MAX_REPORT_BYTES = 2 * 1024 * 1024;
export interface Size { characters: number; utf8_bytes: number; }
export interface OwnerSize extends Size { mcp_tools: number; skill_headers: number; }
export interface ContextSummary {
  total: Size;
  instructions: Size;
  instructionsRaw: Size;
  framing: Size;
  owners: { owner: string; ownership: "declared" | "unattributed"; size: OwnerSize }[];
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected a report object.");
  return value as Record<string, unknown>;
}
function integer(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) throw new Error("Report counts must be finite nonnegative safe integers.");
  return value;
}
function size(value: unknown): Size {
  const row = record(value);
  const result = { characters: integer(row.characters), utf8_bytes: integer(row.utf8_bytes) };
  if (result.utf8_bytes < result.characters) throw new Error("UTF-8 bytes cannot be smaller than Unicode code-point counts.");
  return result;
}
function label(value: unknown): string {
  if (typeof value !== "string" || !value.trim() || value.length > 512 || /[\u0000-\u001f\u007f]/.test(value)) throw new Error("Report labels must be nonempty bounded text without control characters.");
  return value;
}
function add(a: number, b: number): number { return integer(a + b); }
export function validateContextReport(value: unknown): ContextSummary {
  const report = record(value);
  if (report.schema_version !== REPORT_SCHEMA || report.scope !== "caller_supplied_advertised_metadata") throw new Error("Choose a scitex-context-report/1 advertised-metadata report.");
  if (report.normalization !== "UTF-8 compact sorted-key JSON; not protocol framing" || report.instructions_measurement !== "serialized_json_string") throw new Error("Unsupported report measurement convention.");
  if (report.tokens !== null || report.tokenizer !== null || report.client_total_context !== "not_observed") throw new Error("This report version requires unknown tokens, tokenizer and total client context.");
  const total = size(report.total), instructions = size(report.instructions), instructionsRaw = size(report.instructions_raw);
  if (instructions.characters < instructionsRaw.characters + 2 || instructions.utf8_bytes < instructionsRaw.utf8_bytes + 2) throw new Error("Serialized instructions must include JSON string framing.");
  if (!Array.isArray(report.items) || report.items.length > 10000) throw new Error("Expected at most 10,000 measured metadata items.");
  const grouped = new Map<string, OwnerSize>(), identities = new Set<string>();
  let itemCharacters = 0, itemBytes = 0;
  for (const input of report.items) {
    const row = record(input), name = label(row.name);
    if (row.kind !== "mcp_tool" && row.kind !== "skill_header") throw new Error("Unknown measured item kind.");
    const identity = JSON.stringify([row.kind, name]);
    if (identities.has(identity)) throw new Error("Duplicate snapshot identity.");
    identities.add(identity);
    const unknown = row.owner === null;
    const owner = unknown ? "unattributed" : label(row.owner);
    if ((!unknown && owner === "unattributed") || row.ownership !== (unknown ? "unattributed" : "declared")) throw new Error("Ownership must be explicit or unattributed.");
    const measured = size(row), group = grouped.get(owner) || { mcp_tools: 0, skill_headers: 0, characters: 0, utf8_bytes: 0 };
    const count = row.kind === "mcp_tool" ? "mcp_tools" : "skill_headers";
    group[count] = add(group[count], 1);
    group.characters = add(group.characters, measured.characters); group.utf8_bytes = add(group.utf8_bytes, measured.utf8_bytes);
    grouped.set(owner, group); itemCharacters = add(itemCharacters, measured.characters); itemBytes = add(itemBytes, measured.utf8_bytes);
  }
  const packages = record(report.packages);
  if (Object.keys(packages).length !== grouped.size) throw new Error("Owner aggregates do not match measured items.");
  for (const [owner, expected] of grouped) {
    if (!Object.prototype.hasOwnProperty.call(packages, owner)) throw new Error("Missing owner aggregate.");
    const declared = record(packages[owner]), actual = size(declared);
    if (actual.characters !== expected.characters || actual.utf8_bytes !== expected.utf8_bytes || integer(declared.mcp_tools) !== expected.mcp_tools || integer(declared.skill_headers) !== expected.skill_headers) throw new Error("Owner aggregates do not match measured items.");
  }
  const framing = { characters: total.characters - add(itemCharacters, instructions.characters), utf8_bytes: total.utf8_bytes - add(itemBytes, instructions.utf8_bytes) };
  integer(framing.characters); integer(framing.utf8_bytes);
  if (framing.characters !== framing.utf8_bytes) throw new Error("Snapshot JSON framing must be ASCII; report totals are inconsistent.");
  return { total, instructions, instructionsRaw, framing, owners: [...grouped].map(([owner, measured]) => ({ owner, ownership: owner === "unattributed" ? "unattributed" as const : "declared" as const, size: measured })).sort((a, b) => b.size.utf8_bytes - a.size.utf8_bytes || a.owner.localeCompare(b.owner)) };
}
export function parseContextReport(text: string): ContextSummary {
  if (new TextEncoder().encode(text).length > MAX_REPORT_BYTES) throw new Error("Choose a report of at most 2 MiB.");
  let value: unknown;
  try { value = JSON.parse(text); } catch { throw new Error("The file is not valid JSON."); }
  return validateContextReport(value);
}
