/**
 * Git Modals - History and Diff viewers
 * Auto-initializes when imported
 */

export { GitHistoryModal, gitHistoryModal } from './GitHistoryModal';
export { GitDiffModal, gitDiffModal } from './GitDiffModal';

// Initialize both modals when this module is loaded
import './GitHistoryModal.js';
import './GitDiffModal.js';
