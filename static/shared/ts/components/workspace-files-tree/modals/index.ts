/**
 * Git Modals - History and Diff viewers
 * Auto-initializes when imported
 */

export { GitHistoryModal, gitHistoryModal } from './GitHistoryModal.ts';
export { GitDiffModal, gitDiffModal } from './GitDiffModal.ts';

// Initialize both modals when this module is loaded
import './GitHistoryModal.js';
import './GitDiffModal.js';
