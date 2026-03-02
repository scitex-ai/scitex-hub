/**
 * Hub API — fetch wrappers for hub AJAX endpoints.
 */

export async function hubGet(url: string): Promise<any | null> {
  try {
    const resp = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    return resp.ok ? await resp.json() : null;
  } catch {
    return null;
  }
}

export async function hubPost(url: string, body: object): Promise<any | null> {
  try {
    const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
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
    return resp.ok ? await resp.json() : null;
  } catch {
    return null;
  }
}
