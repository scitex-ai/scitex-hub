/**
 * Collaboration Panel Initialization
 * Handles the display of collaborators, chat, and activity in the collaboration view
 */

interface Collaborator {
  username: string;
  isCurrentUser: boolean;
  isOnline: boolean;
  isOwner: boolean;
  currentAction: string;
  lastActivity: string;
}

let collaborators: Collaborator[] = [];
let collaboratorsListElement: HTMLElement | null = null;

/**
 * Get a deterministic color for a username
 */
function getUserColor(username: string): string {
  const colors = [
    '#54aeff', '#ff6b6b', '#51cf66', '#ffa94d',
    '#845ef7', '#ff8787', '#5c7cfa', '#69db7c'
  ];
  const hash = username.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

/**
 * Render collaborator cards in the list
 */
function renderCollaborators(): void {
  if (!collaboratorsListElement) {
    console.error('[CollabPanel] collaboratorsListElement not available');
    return;
  }

  const html = collaborators.map(collab => {
    const avatarColor = getUserColor(collab.username);

    // Determine state
    let statusColor: string, statusTooltip: string, stateLabel: string, stateColor: string;
    if (collab.isOnline) {
      statusColor = '#28a745'; // Green
      statusTooltip = 'Active';
      stateLabel = 'Active';
      stateColor = '#28a745';
    } else {
      statusColor = '#6c757d'; // Gray
      statusTooltip = 'Offline';
      stateLabel = 'Offline';
      stateColor = '#6c757d';
    }

    const ownerBadge = collab.isOwner && collab.isCurrentUser
      ? '<span style="font-weight: 400; color: var(--workspace-text-tertiary); font-size: 11px;"> (Owner)</span>'
      : collab.isCurrentUser
      ? '<span style="font-weight: 400; color: var(--workspace-text-tertiary); font-size: 11px;"> (You)</span>'
      : '';

    // Opacity for offline users
    const cardOpacity = collab.isOnline ? '1' : '0.6';

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
          ${collab.isOnline && collab.currentAction ? `
            <div class="user-current-action" style="font-size: 11px; color: var(--workspace-text-secondary); margin-top: 4px;">
              <i class="fas fa-edit" style="font-size: 9px; margin-right: 4px;"></i>${collab.currentAction}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');

  collaboratorsListElement.innerHTML = html;
  console.log('[CollabPanel] Rendered', collaborators.length, 'collaborator(s)');
}

/**
 * Update current user's activity when switching sections
 */
function updateCurrentUserActivity(): void {
  const activeSectionBtn = document.querySelector('.section-btn.active');
  if (activeSectionBtn && collaborators[0]) {
    const newSection = activeSectionBtn.textContent?.trim() || 'Abstract';
    collaborators[0].currentAction = `Editing ${newSection}`;
    renderCollaborators();
  }
}

/**
 * Update collaborator count text
 */
function updateCollaboratorCount(): void {
  const totalCount = collaborators.length;

  // Update the section title to include count
  const sectionTitle = document.querySelector('.collab-section-modern .section-title-modern span');
  if (sectionTitle) {
    const userText = totalCount === 1 ? 'user' : 'users';
    sectionTitle.textContent = `Collaborators (${totalCount} ${userText})`;
  }
}

/**
 * Initialize the collaborators list
 * This should be called when the collaboration panel is ready
 */
export function initializeCollaboratorsPanel(): void {
  console.log('[CollabPanel] Initializing collaborators list...');

  collaboratorsListElement = document.getElementById('collaborators-list-main');

  if (!collaboratorsListElement) {
    console.error('[CollabPanel] collaborators-list-main element not found');
    return;
  }

  // Check if WRITER_CONFIG is available
  const config = (window as any).WRITER_CONFIG;
  if (!config) {
    console.warn('[CollabPanel] WRITER_CONFIG not available yet, retrying...');
    setTimeout(initializeCollaboratorsPanel, 100);
    return;
  }

  const currentUser = config.username || config.visitorUsername || 'You';
  const projectOwner = config.projectOwner;

  console.log('[CollabPanel] Current user:', currentUser);
  console.log('[CollabPanel] Project owner:', projectOwner);

  // Determine current section from active section button
  let currentSection = 'Abstract';
  const activeSectionBtn = document.querySelector('.section-btn.active');
  if (activeSectionBtn) {
    currentSection = activeSectionBtn.textContent?.trim() || 'Abstract';
  }

  // Build collaborators list - in a real app, this would come from the backend
  // For now, we'll show the current user as active
  collaborators = [
    {
      username: currentUser,
      isCurrentUser: true,
      isOnline: true,
      isOwner: currentUser === projectOwner,
      currentAction: `Editing ${currentSection}`,
      lastActivity: 'Active now'
    }
  ];

  // Render the collaborators
  renderCollaborators();

  // Update counts
  updateCollaboratorCount();

  // Listen for section changes
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains('section-btn')) {
      setTimeout(updateCurrentUserActivity, 100);
    }
  });

  console.log('[CollabPanel] Collaborators initialized successfully');
}

/**
 * Public API to update collaborator list
 * Can be called by WebSocket handlers when collaboration state changes
 */
export function updateCollaborators(newCollaborators: Collaborator[]): void {
  collaborators = newCollaborators;
  renderCollaborators();
  updateCollaboratorCount();
}
