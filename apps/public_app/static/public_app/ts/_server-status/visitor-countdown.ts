/**
 * Visitor Pool Countdown Timers
 */

export function updateVisitorCountdowns(): void {
  document.querySelectorAll('.slot-time-remaining').forEach((element: Element) => {
    const expiresAt = (element as HTMLElement).dataset.expires;
    if (!expiresAt) return;

    const span = element.querySelector('span');
    if (!span) return;

    const now = new Date();
    const expires = new Date(expiresAt);
    const remainingMs = expires.getTime() - now.getTime();
    const remainingSeconds = Math.max(0, Math.floor(remainingMs / 1000));
    const remainingMinutes = Math.floor(remainingSeconds / 60);

    if (remainingSeconds > 0) {
      span.textContent = `Expires in ${remainingMinutes} min`;
    } else {
      span.textContent = 'Expired';
      // Redirect to expired page instead of reloading (prevents infinite reload loop)
      // Use replace() to prevent back button returning to polling page
      window.location.replace('/visitor-expired/');
    }
  });
}
