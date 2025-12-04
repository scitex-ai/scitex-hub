/**
 * Visitor Manager
 * Handles visitor detection, permissions, and warnings
 */

import type { EditorConfig } from "../core/types.js";

export class VisitorManager {
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
  }

  /**
   * Check if current user is a visitor (guest session)
   */
  isVisitor(): boolean {
    const owner = this.config.currentProject?.owner;
    return owner ? owner.startsWith("visitor-") : false;
  }

  /**
   * Show signup warning modal for visitors
   */
  showSignupWarning(): void {
    const modal = document.getElementById("signup-warning-modal");
    if (modal) {
      modal.classList.add("active");
    }
  }

  /**
   * Show one-time warning to visitors that their work is temporary
   * Displays a toast notification once per session
   */
  showVisitorWarningOnce(): void {
    // Check if warning already shown in this session
    const warningShown = sessionStorage.getItem("visitor_warning_shown");
    if (warningShown) {
      return;
    }

    // Show toast-style notification
    const toast = document.createElement("div");
    toast.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      max-width: 400px;
      background: var(--workspace-bg-secondary);
      border-left: 3px solid var(--status-warning);
      border-radius: 6px;
      padding: 16px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      z-index: 9999;
      animation: slideIn 0.3s ease;
    `;

    toast.innerHTML = `
      <div style="display: flex; align-items: start; gap: 12px;">
        <i class="fas fa-info-circle" style="color: var(--status-warning); font-size: 20px; flex-shrink: 0;"></i>
        <div style="flex: 1;">
          <strong style="color: var(--text-default); display: block; margin-bottom: 6px;">Visitor Mode</strong>
          <p style="color: var(--text-muted); margin: 0; font-size: 13px; line-height: 1.5;">
            You can create and edit files, but your 60-minute session will expire.
            <a href="/accounts/signup/" style="color: var(--workspace-icon-primary); text-decoration: none;">
              Sign up free
            </a> to save permanently.
          </p>
        </div>
        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 0; font-size: 18px;">×</button>
      </div>
    `;

    // Add slide-in animation
    const style = document.createElement("style");
    style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
    `;
    document.head.appendChild(style);

    document.body.appendChild(toast);

    // Auto-remove after 8 seconds
    setTimeout(() => {
      toast.style.animation = "slideIn 0.3s ease reverse";
      setTimeout(() => toast.remove(), 300);
    }, 8000);

    // Mark as shown
    sessionStorage.setItem("visitor_warning_shown", "true");
  }
}
