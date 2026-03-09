/**
 * Initialize Git Gutter for File Tree
 * This script initializes the git gutter service when the page loads
 */

import { DirectoryGutterService } from './components/GitGutter';

// Initialize git gutter when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Get project info from the page
    const pathParts = window.location.pathname.split('/').filter(p => p);

    // Expect URL format: /<username>/<slug>/...
    if (pathParts.length < 2) {
        console.warn('[GitGutter] Unable to determine project from URL');
        return;
    }

    const username = pathParts[0];
    const slug = pathParts[1];

    console.log(`[GitGutter] Initializing for ${username}/${slug}`);

    // Create and start git gutter service
    const gitGutter = new DirectoryGutterService(username, slug);

    // Start auto-updating every 30 seconds
    gitGutter.startAutoUpdate(30000);

    // Make it globally accessible for debugging
    (window as any).gitGutter = gitGutter;

    console.log('[GitGutter] Initialized successfully');
});
