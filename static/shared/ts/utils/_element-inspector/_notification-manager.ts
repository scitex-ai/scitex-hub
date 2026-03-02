/**
 * Notification Manager for Element Inspector
 * Handles notifications and visual effects (minimal style)
 */

export class NotificationManager {
  private onCopyCallback: (() => void) | null = null;

  /**
   * Set callback to be called after successful copy
   * Used to trigger ESC/deactivate after copy
   */
  public setOnCopyCallback(callback: () => void): void {
    this.onCopyCallback = callback;
  }

  /**
   * Trigger the copy callback (called after successful copy)
   */
  public triggerCopyCallback(): void {
    if (this.onCopyCallback) {
      // Small delay to let notification show briefly
      setTimeout(() => {
        this.onCopyCallback?.();
      }, 400);
    }
  }

  public showNotification(
    message: string,
    type: "success" | "error",
    duration: number = 1000,
  ): void {
    const notification = document.createElement("div");
    notification.textContent = message;
    // Visible but compact style
    notification.style.cssText = `
            position: fixed;
            top: 16px;
            right: 16px;
            padding: 10px 20px;
            background: ${type === "success" ? "rgba(16, 185, 129, 0.95)" : "rgba(239, 68, 68, 0.95)"};
            color: white;
            border-radius: 6px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 600;
            z-index: 10000000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            opacity: 0;
            transform: translateY(-10px) scale(0.95);
            transition: opacity 0.2s ease, transform 0.2s ease;
        `;

    document.body.appendChild(notification);

    // Animate in
    requestAnimationFrame(() => {
      notification.style.opacity = "1";
      notification.style.transform = "translateY(0) scale(1)";
    });

    // Show for specified duration
    setTimeout(() => {
      notification.style.opacity = "0";
      notification.style.transform = "translateY(-10px) scale(0.95)";
      setTimeout(() => notification.remove(), 200);
    }, duration);
  }

  public showCameraFlash(): void {
    // Brief flash overlay
    const flash = document.createElement("div");
    flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.4);
            z-index: 9999999;
            pointer-events: none;
            opacity: 1;
            transition: opacity 0.1s ease;
        `;
    document.body.appendChild(flash);

    // Fade out quickly
    setTimeout(() => {
      flash.style.opacity = "0";
    }, 30);

    setTimeout(() => {
      flash.remove();
    }, 130);
  }
}
