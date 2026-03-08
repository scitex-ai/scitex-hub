/**
 * Bash execution helper for the AI chat "!" prefix mode.
 */

import { API_URLS } from "../../utils/api-urls";

export interface BashResult {
  text: string;
  returncode: number | undefined;
}

export async function execBashCommand(
  command: string,
  projectSlug: string | null,
  csrfToken: string,
): Promise<BashResult> {
  const resp = await fetch(API_URLS.llm.bash, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ command, project_slug: projectSlug }),
  });

  const d = (await resp.json()) as {
    stdout?: string;
    stderr?: string;
    returncode?: number;
    error?: string;
  };

  const text = d.error
    ? `Error: ${d.error}`
    : `${d.stdout ?? ""}${d.stderr ? `\nstderr: ${d.stderr}` : ""}`.trim() ||
      "(no output)";

  return { text, returncode: d.returncode };
}
