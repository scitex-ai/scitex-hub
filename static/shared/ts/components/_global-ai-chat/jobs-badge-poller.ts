/**
 * Jobs Badge Poller
 * Polls /apps/console/api/jobs/ periodically and updates the jobs badge count.
 */

const BADGE_POLL_INTERVAL = 10_000;

export function startJobsBadgePoller(): void {
  const update = async () => {
    try {
      const resp = await fetch("/apps/console/api/jobs/");
      if (!resp.ok) return;
      const data = await resp.json();
      const n = (data.running || 0) + (data.pending || 0);
      for (const id of ["jobs-badge"]) {
        const el = document.getElementById(id);
        if (el) {
          el.textContent = String(n);
          el.style.display = n > 0 ? "" : "none";
        }
      }
    } catch {
      /* silent */
    }
  };
  void update();
  setInterval(() => void update(), BADGE_POLL_INTERVAL);
}
