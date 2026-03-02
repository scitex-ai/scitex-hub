/**
 * Presence Display - Shows active collaborators in real-time
 *
 * Displays who's online, what they're editing, and provides visual feedback
 */

console.log("[DEBUG] presence-display.ts loaded");

interface Collaborator {
  user_id: number;
  username: string;
  is_active: boolean;
  locked_sections?: string[];
  current_section?: string;
  color?: string;
}

export class PresenceDisplay {
  private container: HTMLElement | null = null;
  private collaborators: Map<number, Collaborator> = new Map();
  private colorPalette: string[] = [
    "#FF6B6B", // Red
    "#4ECDC4", // Teal
    "#45B7D1", // Blue
    "#FFA07A", // Light Salmon
    "#98D8C8", // Mint
    "#F7DC6F", // Yellow
    "#BB8FCE", // Purple
    "#85C1E2", // Sky Blue
  ];
  private colorIndex: number = 0;

  constructor(containerId: string = "collaborators-list-main") {
    this.container = document.getElementById(containerId);

    if (!this.container) {
      console.warn(`[PresenceDisplay] Container #${containerId} not found, creating one`);
      this.createContainer(containerId);
    }

    this.injectStyles();
  }

  /**
   * Create container if it doesn't exist
   */
  private createContainer(containerId: string): void {
    this.container = document.createElement("div");
    this.container.id = containerId;
    this.container.className = "collaborators-container";

    // Try to append to a known location or body
    const collabSection = document.querySelector(".collaborators-section .section-body");
    if (collabSection) {
      collabSection.appendChild(this.container);
    } else {
      const sidebar = document.querySelector(".sidebar");
      if (sidebar) {
        sidebar.appendChild(this.container);
      } else {
        document.body.appendChild(this.container);
      }
    }
  }

  /**
   * Update collaborators list
   */
  updateCollaborators(collaborators: Collaborator[]): void {
    // Clear and rebuild
    this.collaborators.clear();

    collaborators.forEach((collab) => {
      // Assign colors to new collaborators
      if (!collab.color) {
        collab.color = this.getNextColor();
      }
      this.collaborators.set(collab.user_id, collab);
    });

    this.render();
  }

  /**
   * Add a single collaborator
   */
  addCollaborator(collaborator: Collaborator): void {
    if (!collaborator.color) {
      collaborator.color = this.getNextColor();
    }
    this.collaborators.set(collaborator.user_id, collaborator);
    this.render();
  }

  /**
   * Remove a collaborator
   */
  removeCollaborator(userId: number): void {
    this.collaborators.delete(userId);
    this.render();
  }

  /**
   * Update a collaborator's current section
   */
  updateCollaboratorSection(userId: number, section: string): void {
    const collaborator = this.collaborators.get(userId);
    if (collaborator) {
      collaborator.current_section = section;
      this.render();
    }
  }

  /**
   * Render the presence display
   */
  private render(): void {
    if (!this.container) return;

    const collaboratorCount = this.collaborators.size;

    if (collaboratorCount === 0) {
      this.container.innerHTML = `
        <div class="presence-header">
          <h3>Active Collaborators</h3>
          <span class="collab-count">0</span>
        </div>
        <div class="presence-empty">
          <p>No other users are currently editing</p>
        </div>
      `;
      return;
    }

    const collaboratorsList = Array.from(this.collaborators.values());

    this.container.innerHTML = `
      <div class="presence-header">
        <h3>Active Collaborators</h3>
        <span class="collab-count">${collaboratorCount}</span>
      </div>
      <div class="presence-list">
        ${collaboratorsList.map((collab) => this.renderCollaborator(collab)).join("")}
      </div>
    `;
  }

  /**
   * Render a single collaborator
   */
  private renderCollaborator(collab: Collaborator): string {
    const statusClass = collab.is_active ? "active" : "inactive";
    const statusColor = collab.is_active ? "#28a745" : "#dc3545"; // Green or Red

    return `
      <div class="collaborator-item ${statusClass}" data-user-id="${collab.user_id}">
        <div class="collaborator-avatar" style="background-color: ${collab.color}">
          ${this.getInitials(collab.username)}
        </div>
        <div class="collaborator-name">${this.escapeHtml(collab.username)}</div>
        <div class="collaborator-indicator" style="background-color: ${statusColor}"></div>
      </div>
    `;
  }

  /**
   * Get initials from username
   */
  private getInitials(username: string): string {
    const parts = username.split(/[\s_-]+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return username.substring(0, 2).toUpperCase();
  }

  /**
   * Format section name for display
   */
  private formatSectionName(section: string): string {
    return section
      .split(/[-_]/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Get next color from palette
   */
  private getNextColor(): string {
    const color = this.colorPalette[this.colorIndex];
    this.colorIndex = (this.colorIndex + 1) % this.colorPalette.length;
    return color;
  }

  /**
   * Clear all collaborators
   */
  clear(): void {
    this.collaborators.clear();
    this.render();
  }

  /**
   * Inject CSS styles
   */
  private injectStyles(): void {
    if (document.getElementById("presence-display-styles")) {
      return; // Already injected
    }

    const style = document.createElement("style");
    style.id = "presence-display-styles";
    style.textContent = `
      .collaborators-container {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
      }

      .presence-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 2px solid #e9ecef;
      }

      .presence-header h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #2c3e50;
      }

      .collab-count {
        background: #007bff;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
      }

      .presence-empty {
        text-align: center;
        padding: 24px;
        color: #6c757d;
      }

      .presence-empty p {
        margin: 0;
        font-size: 14px;
      }

      .presence-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0;
      }

      .collaborator-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 8px;
        background: var(--color-canvas-subtle, #f6f8fa);
        border-radius: 16px;
        transition: all 0.2s ease;
        margin: 0 4px 4px 0;
        border: 1px solid var(--color-border-default, #d1d5da);
      }

      .collaborator-item:hover {
        background: var(--color-canvas-default, #fff);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      }

      .collaborator-avatar {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 600;
        color: white;
        flex-shrink: 0;
      }

      .collaborator-name {
        font-size: 12px;
        font-weight: 500;
        color: var(--color-fg-default, #24292e);
        white-space: nowrap;
      }

      .collaborator-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.3);
      }

      .collaborator-item.active .collaborator-indicator {
        animation: pulse 2s infinite;
      }

      @keyframes pulse {
        0%, 100% {
          opacity: 1;
          transform: scale(1);
        }
        50% {
          opacity: 0.5;
          transform: scale(1.1);
        }
      }
    `;

    document.head.appendChild(style);
  }
}

// Export for global access
declare global {
  interface Window {
    PresenceDisplay: typeof PresenceDisplay;
  }
}

window.PresenceDisplay = PresenceDisplay;
