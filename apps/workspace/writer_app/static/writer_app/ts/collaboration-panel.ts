/**
 * Collaboration Panel Initialization
 *
 * Displays real-time collaborator presence, online/offline status,
 * cursor positions, and section-lock state. Fed by WriterWSClient events.
 */

interface Collaborator {
  user_id: number;
  username: string;
  isCurrentUser: boolean;
  isOnline: boolean;
  isOwner: boolean;
  currentAction: string;
  lastActivity: string;
  lockedSections: string[];
}

let collaborators: Collaborator[] = [];
let collaboratorsListElement: HTMLElement | null = null;
let currentUsername = "";
let projectOwner = "";

/**
 * Get a deterministic color for a username
 */
function getUserColor(username: string): string {
  const colors = [
    "#54aeff",
    "#ff6b6b",
    "#51cf66",
    "#ffa94d",
    "#845ef7",
    "#ff8787",
    "#5c7cfa",
    "#69db7c",
  ];
  const hash = username
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

/**
 * Render collaborator cards in the list
 */
function renderCollaborators(): void {
  if (!collaboratorsListElement) {
    console.error("[CollabPanel] collaboratorsListElement not available");
    return;
  }

  const html = collaborators
    .map((collab) => {
      const avatarColor = getUserColor(collab.username);

      let statusColor: string, statusTooltip: string;
      if (collab.isOnline) {
        statusColor = "#28a745";
        statusTooltip = "Active";
      } else {
        statusColor = "#6c757d";
        statusTooltip = "Offline";
      }

      const ownerBadge =
        collab.isOwner && collab.isCurrentUser
          ? '<span style="font-weight: 400; color: var(--workspace-text-tertiary); font-size: 11px;"> (Owner)</span>'
          : collab.isCurrentUser
            ? '<span style="font-weight: 400; color: var(--workspace-text-tertiary); font-size: 11px;"> (You)</span>'
            : "";

      const cardOpacity = collab.isOnline ? "1" : "0.6";

      // Show lock info if user has locked sections
      const lockInfo =
        collab.lockedSections.length > 0
          ? `<div style="font-size: 10px; color: ${avatarColor}; margin-top: 2px;"><i class="fas fa-lock" style="font-size: 9px; margin-right: 3px;"></i>${collab.lockedSections.join(", ")}</div>`
          : "";

      return `
      <div class="collaborator-card" style="background: var(--workspace-bg-secondary); border: 1px solid var(--workspace-border-default); border-radius: 6px; padding: 10px 12px; display: flex; align-items: center; gap: 10px; transition: all 0.2s ease; opacity: ${cardOpacity};">
        <div class="user-avatar" style="width: 36px; height: 36px; border-radius: 50%; background: ${avatarColor}; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 14px; flex-shrink: 0; position: relative;" title="${collab.username}">
          ${collab.username.substring(0, 2).toUpperCase()}
          <div style="position: absolute; bottom: -2px; right: -2px; width: 12px; height: 12px; background: ${statusColor}; border: 2px solid var(--workspace-bg-secondary); border-radius: 50%;" title="${statusTooltip}"></div>
        </div>
        <div style="flex: 1; min-width: 0;">
          <div style="font-size: 13px; font-weight: 600; color: var(--workspace-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${collab.username}${ownerBadge}
          </div>
          ${
            collab.isOnline && collab.currentAction
              ? `
            <div class="user-current-action" style="font-size: 11px; color: var(--workspace-text-secondary); margin-top: 4px;">
              <i class="fas fa-edit" style="font-size: 9px; margin-right: 4px;"></i>${collab.currentAction}
            </div>
          `
              : ""
          }
          ${lockInfo}
        </div>
      </div>
    `;
    })
    .join("");

  collaboratorsListElement.innerHTML = html;
  console.log(
    "[CollabPanel] Rendered",
    collaborators.length,
    "collaborator(s)",
  );
}

/**
 * Update current user's activity when switching sections
 */
function updateCurrentUserActivity(): void {
  const activeSectionBtn = document.querySelector(".section-btn.active");
  const me = collaborators.find((c) => c.isCurrentUser);
  if (activeSectionBtn && me) {
    const newSection = activeSectionBtn.textContent?.trim() || "Abstract";
    me.currentAction = `Editing ${newSection}`;
    renderCollaborators();
  }
}

/**
 * Update collaborator count text
 */
function updateCollaboratorCount(): void {
  const totalCount = collaborators.length;
  const onlineCount = collaborators.filter((c) => c.isOnline).length;

  const sectionTitle = document.querySelector(
    ".collab-section-modern .section-title-modern span",
  );
  if (sectionTitle) {
    const userText = totalCount === 1 ? "user" : "users";
    sectionTitle.textContent = `Collaborators (${onlineCount}/${totalCount} ${userText} online)`;
  }
}

// ---------------------------------------------------------------- public API

/**
 * Initialize the collaborators list.
 * Should be called when the collaboration panel DOM is ready.
 */
export function initializeCollaboratorsPanel(): void {
  console.log("[CollabPanel] Initializing collaborators list...");

  collaboratorsListElement = document.getElementById("collaborators-list-main");

  if (!collaboratorsListElement) {
    console.error("[CollabPanel] collaborators-list-main element not found");
    return;
  }

  const config = (window as any).WRITER_CONFIG;
  if (!config) {
    console.warn("[CollabPanel] WRITER_CONFIG not available yet, retrying...");
    setTimeout(initializeCollaboratorsPanel, 100);
    return;
  }

  currentUsername = config.username || config.visitorUsername || "You";
  projectOwner = config.projectOwner || "";

  console.log("[CollabPanel] Current user:", currentUsername);
  console.log("[CollabPanel] Project owner:", projectOwner);

  let currentSection = "Abstract";
  const activeSectionBtn = document.querySelector(".section-btn.active");
  if (activeSectionBtn) {
    currentSection = activeSectionBtn.textContent?.trim() || "Abstract";
  }

  // Seed with current user; the WebSocket will add remote collaborators
  collaborators = [
    {
      user_id: 0,
      username: currentUsername,
      isCurrentUser: true,
      isOnline: true,
      isOwner: currentUsername === projectOwner,
      currentAction: `Editing ${currentSection}`,
      lastActivity: "Active now",
      lockedSections: [],
    },
  ];

  renderCollaborators();
  updateCollaboratorCount();

  document.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains("section-btn")) {
      setTimeout(updateCurrentUserActivity, 100);
    }
  });

  console.log("[CollabPanel] Collaborators initialized successfully");
}

/**
 * Called by the WebSocket client when the initial collaborators_list arrives.
 * Replaces the remote entries while keeping the local (current) user entry.
 */
export function handleCollaboratorsList(
  serverCollaborators: {
    user_id: number;
    username: string;
    locked_sections: string[];
  }[],
): void {
  const me = collaborators.find((c) => c.isCurrentUser);

  collaborators = serverCollaborators.map((sc) => {
    const isMe = sc.username === currentUsername;
    if (isMe && me) {
      // Keep local state for current user
      me.user_id = sc.user_id;
      me.lockedSections = sc.locked_sections;
      return me;
    }
    return {
      user_id: sc.user_id,
      username: sc.username,
      isCurrentUser: false,
      isOnline: true,
      isOwner: sc.username === projectOwner,
      currentAction: "",
      lastActivity: "Active now",
      lockedSections: sc.locked_sections,
    };
  });

  // If current user was not in the server list (should not happen), re-add
  if (!collaborators.find((c) => c.isCurrentUser) && me) {
    collaborators.unshift(me);
  }

  renderCollaborators();
  updateCollaboratorCount();
}

/**
 * Called when a user_joined event arrives.
 */
export function handleUserJoined(userId: number, username: string): void {
  if (username === currentUsername) return; // ignore self echo

  const existing = collaborators.find((c) => c.user_id === userId);
  if (existing) {
    existing.isOnline = true;
    existing.lastActivity = "Active now";
  } else {
    collaborators.push({
      user_id: userId,
      username,
      isCurrentUser: false,
      isOnline: true,
      isOwner: username === projectOwner,
      currentAction: "",
      lastActivity: "Active now",
      lockedSections: [],
    });
  }

  renderCollaborators();
  updateCollaboratorCount();
}

/**
 * Called when a user_left event arrives.
 */
export function handleUserLeft(userId: number, _username: string): void {
  const collab = collaborators.find((c) => c.user_id === userId);
  if (collab) {
    collab.isOnline = false;
    collab.currentAction = "";
    collab.lockedSections = [];
  }
  renderCollaborators();
  updateCollaboratorCount();
}

/**
 * Update the displayed current-section for a remote user (from cursor_update).
 */
export function handleRemoteCursorUpdate(
  userId: number,
  _username: string,
  section: string,
): void {
  const collab = collaborators.find((c) => c.user_id === userId);
  if (collab && !collab.isCurrentUser) {
    collab.currentAction = `Viewing ${section}`;
    renderCollaborators();
  }
}

/**
 * Mark a section as locked by a user in the panel display.
 */
export function handleSectionLocked(
  userId: number,
  _username: string,
  section: string,
): void {
  const collab = collaborators.find((c) => c.user_id === userId);
  if (collab && !collab.lockedSections.includes(section)) {
    collab.lockedSections.push(section);
    renderCollaborators();
  }
}

/**
 * Mark a section as unlocked by a user in the panel display.
 */
export function handleSectionUnlocked(
  userId: number,
  _username: string,
  section: string,
): void {
  const collab = collaborators.find((c) => c.user_id === userId);
  if (collab) {
    collab.lockedSections = collab.lockedSections.filter((s) => s !== section);
    renderCollaborators();
  }
}

/**
 * Update panel to reflect WebSocket connection state.
 */
export function handleConnectionChange(connected: boolean): void {
  const indicator = document.getElementById("ws-connection-indicator");
  if (indicator) {
    indicator.style.background = connected ? "#28a745" : "#dc3545";
    indicator.title = connected ? "Connected" : "Disconnected";
  }
}

/**
 * Legacy API -- replace full collaborator list (kept for backward compatibility).
 */
export function updateCollaborators(newCollaborators: Collaborator[]): void {
  collaborators = newCollaborators;
  renderCollaborators();
  updateCollaboratorCount();
}
