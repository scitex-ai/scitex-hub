/**
 * Shared sections-config request. Four modules asked for it on page load;
 * concurrent callers now share one request (reused briefly, never cached
 * past a section create/delete).
 */
const URL = "/apps/writer/api/sections-config/";
const REUSE_MS = 1500;

let pending: Promise<any> | null = null;

export function fetchSectionsConfig(): Promise<any> {
  if (pending) return pending;
  const request = fetch(URL).then((response) => response.json());
  pending = request;
  const release = () => {
    window.setTimeout(() => {
      if (pending === request) pending = null;
    }, REUSE_MS);
  };
  request.then(release, () => {
    pending = null;
  });
  return request;
}
