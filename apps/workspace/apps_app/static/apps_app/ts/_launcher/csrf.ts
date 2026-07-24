/** CSRF token lookup shared by the launcher's POSTs (reorder, pin). */
export function getCsrf(): string {
  const input = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement | null;
  if (input) return input.value;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}
