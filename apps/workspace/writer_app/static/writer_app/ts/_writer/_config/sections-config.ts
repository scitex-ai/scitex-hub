/**
 * Shared sections-config request. Four modules asked for it on page load;
 * concurrent callers now share one request (reused briefly, never cached
 * past a section create/delete).
 */
const URL = "/apps/writer/api/sections-config/";
const REUSE_MS = 1500;

let pending: Promise<any> | null = null;
let releaseScheduled = false;

function start(): Promise<any> {
  const request = fetch(URL).then((response) => response.json());
  pending = request;
  releaseScheduled = false;
  request.catch(() => {
    if (pending === request) pending = null;
  });
  return request;
}

/** Fire the request while the bundle is still booting; first reader reuses it. */
export function prefetchSectionsConfig(): void {
  if (!pending) start();
}

export function fetchSectionsConfig(): Promise<any> {
  const request = pending || start();
  if (!releaseScheduled) {
    releaseScheduled = true;
    const release = () =>
      window.setTimeout(() => {
        if (pending === request) pending = null;
      }, REUSE_MS);
    request.then(release, release);
  }
  return request;
}
