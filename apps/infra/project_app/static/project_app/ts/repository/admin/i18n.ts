/**
 * Interim string catalog for the Project Health page.
 *
 * The page template emits the translated strings once, server-side, as
 *   {{ project_health_i18n|json_script:"project-health-i18n" }}
 * (built by apps/infra/accounts_app/views/project_health_i18n.py), and this
 * module reads that JSON a single time. Every call site passes the English
 * source string as the fallback, so a page that ships no catalog (e.g. the
 * legacy project_app maintenance page) still renders English.
 *
 * INTERIM: scitex-ui is building a shell-level i18n primitive. The keys here
 * are stable dotted names ("card.healthy.label", ...) and the only entry point
 * is t(key, fallbackEnglish), so swapping this module for that primitive is a
 * mechanical replacement of the import — keep keys unchanged when doing so.
 *
 * Catalog values are plain text: render them with textContent / DOM building,
 * never innerHTML.
 *
 * @module repository/admin/i18n
 */

export const CATALOG_ELEMENT_ID = "project-health-i18n";

type Catalog = Record<string, string>;

let catalog: Catalog | null = null;

function readCatalog(): Catalog {
  const el = document.getElementById(CATALOG_ELEMENT_ID);
  if (!el || !el.textContent) {
    return {};
  }
  try {
    const parsed: unknown = JSON.parse(el.textContent);
    return parsed && typeof parsed === "object" ? (parsed as Catalog) : {};
  } catch {
    return {};
  }
}

/**
 * Returns the translated string for `key`, or `fallback` (the English source)
 * when the page carries no catalog or the key is missing.
 */
export function t(key: string, fallback: string): string {
  if (catalog === null) {
    catalog = readCatalog();
  }
  const value = catalog[key];
  return typeof value === "string" && value !== "" ? value : fallback;
}

/** Forgets the cached catalog so the next t() re-reads the page. */
export function resetCatalog(): void {
  catalog = null;
}
