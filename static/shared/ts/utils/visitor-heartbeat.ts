/**
 * Visitor Session Heartbeat
 *
 * Sends periodic heartbeats to the server while the user is active.
 * This allows the server to track idle time and manage session resources.
 */

const HEARTBEAT_INTERVAL_MS = 30000; // 30 seconds
const IDLE_THRESHOLD_MS = 60000; // 1 minute of no activity = idle

interface HeartbeatResponse {
  status: string;
  remaining_seconds: number;
  expires_at: string;
}

class VisitorHeartbeat {
  private intervalId: number | null = null;
  private lastActivity: number = Date.now();
  private isIdle: boolean = false;

  constructor() {
    // Don't run on visitor-expired page (prevents redirect loop)
    if (window.location.pathname.includes('visitor-expired')) {
      return;
    }

    // Only run for visitor users
    const isVisitor = document.body.dataset.userType === 'visitor';
    if (!isVisitor) {
      return;
    }

    this.setupActivityListeners();
    this.startHeartbeat();
  }

  private setupActivityListeners(): void {
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, () => this.onActivity(), { passive: true });
    });
  }

  private onActivity(): void {
    this.lastActivity = Date.now();
    if (this.isIdle) {
      this.isIdle = false;
      console.log('[Heartbeat] User became active');
      this.sendHeartbeat(); // Immediate heartbeat when becoming active
    }
  }

  private startHeartbeat(): void {
    // Send initial heartbeat
    this.sendHeartbeat();

    // Set up interval
    this.intervalId = window.setInterval(() => {
      const idleTime = Date.now() - this.lastActivity;

      if (idleTime > IDLE_THRESHOLD_MS) {
        if (!this.isIdle) {
          this.isIdle = true;
          console.log('[Heartbeat] User became idle');
        }
        // Skip heartbeat when idle to allow resource release
        return;
      }

      this.sendHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);
  }

  private async sendHeartbeat(): Promise<void> {
    try {
      const response = await fetch('/api/visitor/heartbeat/', {
        method: 'GET',
        credentials: 'same-origin',
      });

      if (response.ok) {
        const data: HeartbeatResponse = await response.json();
        console.log(`[Heartbeat] Session active, ${Math.floor(data.remaining_seconds / 60)} min remaining`);

        // Warn user when session is about to expire (5 min warning)
        if (data.remaining_seconds <= 300 && data.remaining_seconds > 240) {
          this.showSessionWarning(data.remaining_seconds);
        }
      } else if (response.status === 404 || response.status === 401 || response.status === 403) {
        // Session expired - redirect to expired page (not reload to prevent infinite loop)
        console.log('[Heartbeat] Session expired, redirecting to visitor-expired');
        this.destroy(); // Stop heartbeat before redirect
        window.location.replace('/visitor-expired/');
      }
    } catch (error) {
      console.warn('[Heartbeat] Error:', error);
    }
  }

  private showSessionWarning(remainingSeconds: number): void {
    const minutes = Math.ceil(remainingSeconds / 60);
    // Check if warning already shown
    if (document.querySelector('.session-warning-toast')) {
      return;
    }

    const toast = document.createElement('div');
    toast.className = 'session-warning-toast alert alert-warning position-fixed';
    toast.style.cssText = 'bottom: 20px; right: 20px; z-index: 9999; max-width: 350px;';
    toast.innerHTML = `
      <strong>Session Expiring</strong><br>
      Your visitor session will expire in ${minutes} minutes.
      <a href="/signup/" class="alert-link">Create an account</a> for unlimited access.
    `;

    document.body.appendChild(toast);

    // Auto-remove after 30 seconds
    setTimeout(() => toast.remove(), 30000);
  }

  public destroy(): void {
    if (this.intervalId) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new VisitorHeartbeat());
} else {
  new VisitorHeartbeat();
}

export { VisitorHeartbeat };
