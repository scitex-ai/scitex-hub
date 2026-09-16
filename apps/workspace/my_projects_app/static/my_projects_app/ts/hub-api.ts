/**
 * Hub API — fetch wrappers for hub AJAX endpoints.
 */

import { getCsrfToken } from "@utils/csrf";

export async function hubGet(url: string): Promise<any | null> {
  try {
    const resp = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!resp.ok) {
      console.error(`[hub-api] GET ${url} failed: HTTP ${resp.status}`);
      return null;
    }
    return await resp.json();
  } catch (err) {
    console.error(`[hub-api] GET ${url} failed:`, err);
    return null;
  }
}

export async function hubPost(url: string, body: object): Promise<any | null> {
  try {
    // getCsrfToken reads the hidden csrfmiddlewaretoken input first —
    // production sets CSRF_COOKIE_HTTPONLY, so document.cookie NEVER
    // exposes csrftoken there and the old cookie-only lookup sent an
    // empty X-CSRFToken: every hub POST (e.g. select-project on a
    // project-card click) 403'd silently (nav-404 batch #9).
    const csrfToken = getCsrfToken();
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      console.error(`[hub-api] POST ${url} failed: HTTP ${resp.status}`);
      return null;
    }
    return await resp.json();
  } catch (err) {
    console.error(`[hub-api] POST ${url} failed:`, err);
    return null;
  }
}
