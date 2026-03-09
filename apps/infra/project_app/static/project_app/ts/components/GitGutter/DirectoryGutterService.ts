/**
 * Directory Git Gutter Service
 * Adds visual indicators to the file tree showing git status (modified, added, deleted, untracked)
 */

export interface FileGitStatus {
    path: string;
    status: 'modified' | 'added' | 'deleted' | 'untracked' | 'renamed' | 'copied';
    staged: boolean;
    changes?: number;
}

export interface GitStatusResponse {
    success: boolean;
    files: FileGitStatus[];
    branch: string;
    ahead: number;
    behind: number;
}

export class DirectoryGutterService {
    private statusCache: Map<string, FileGitStatus> = new Map();
    private updateInterval: number | null = null;
    private username: string;
    private slug: string;

    constructor(username: string, slug: string) {
        this.username = username;
        this.slug = slug;
    }

    /**
     * Start auto-updating git status indicators
     * @param intervalMs - Update interval in milliseconds (default: 30000 = 30s)
     */
    startAutoUpdate(intervalMs: number = 30000): void {
        this.updateGutters();
        this.updateInterval = window.setInterval(() => {
            this.updateGutters();
        }, intervalMs);
    }

    /**
     * Stop auto-updating
     */
    stopAutoUpdate(): void {
        if (this.updateInterval !== null) {
            window.clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Fetch git status from API
     */
    async fetchGitStatus(): Promise<GitStatusResponse> {
        try {
            const response = await fetch(`/${this.username}/${this.slug}/api/git/status/`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();

            // Update cache
            this.statusCache.clear();
            if (data.files) {
                data.files.forEach((file: FileGitStatus) => {
                    this.statusCache.set(file.path, file);
                });
            }

            return data;
        } catch (error) {
            console.error('[GitGutter] Failed to fetch git status:', error);
            return {
                success: false,
                files: [],
                branch: '',
                ahead: 0,
                behind: 0
            };
        }
    }

    /**
     * Update all git gutter indicators in the file tree
     */
    async updateGutters(): Promise<void> {
        const statusData = await this.fetchGitStatus();
        if (!statusData.success) {
            console.warn('[GitGutter] Git status fetch failed');
            return;
        }

        // Update each file in the tree
        statusData.files.forEach(fileStatus => {
            this.updateFileIndicator(fileStatus);
        });

        // Update branch info if available
        this.updateBranchInfo(statusData);
    }

    /**
     * Update git indicator for a single file
     */
    private updateFileIndicator(fileStatus: FileGitStatus): void {
        // Find the file tree item by path
        const fileItems = document.querySelectorAll('.file-tree-item');

        fileItems.forEach(item => {
            const link = item.querySelector('a');
            if (!link) return;

            const href = link.getAttribute('href') || '';

            // Check if this item corresponds to our file
            if (href.includes(fileStatus.path)) {
                // Remove any existing git gutter indicator
                const existingIndicator = item.querySelector('.git-gutter-indicator');
                if (existingIndicator) {
                    existingIndicator.remove();
                }

                // Create new indicator
                const indicator = this.createIndicator(fileStatus);

                // Insert indicator before the icon
                const icon = item.querySelector('.file-tree-icon');
                if (icon) {
                    icon.insertAdjacentElement('beforebegin', indicator);
                }
            }
        });
    }

    /**
     * Create a git status indicator element
     */
    private createIndicator(fileStatus: FileGitStatus): HTMLElement {
        const indicator = document.createElement('span');
        indicator.className = `git-gutter-indicator git-gutter-${fileStatus.status}`;

        if (fileStatus.staged) {
            indicator.classList.add('git-gutter-staged');
        }

        // Set tooltip
        let tooltipText = '';
        switch (fileStatus.status) {
            case 'modified':
                tooltipText = fileStatus.staged ? 'Modified (staged)' : 'Modified';
                break;
            case 'added':
                tooltipText = fileStatus.staged ? 'Added (staged)' : 'Added';
                break;
            case 'deleted':
                tooltipText = 'Deleted';
                break;
            case 'untracked':
                tooltipText = 'Untracked';
                break;
            case 'renamed':
                tooltipText = 'Renamed';
                break;
            case 'copied':
                tooltipText = 'Copied';
                break;
        }

        if (fileStatus.changes) {
            tooltipText += ` (${fileStatus.changes} changes)`;
        }

        indicator.title = tooltipText;
        indicator.setAttribute('data-git-status', fileStatus.status);

        return indicator;
    }

    /**
     * Update branch info display (if exists)
     */
    private updateBranchInfo(statusData: GitStatusResponse): void {
        const branchInfo = document.getElementById('git-branch-info');
        if (!branchInfo) return;

        let statusText = statusData.branch;

        if (statusData.ahead > 0) {
            statusText += ` ↑${statusData.ahead}`;
        }

        if (statusData.behind > 0) {
            statusText += ` ↓${statusData.behind}`;
        }

        branchInfo.textContent = statusText;
    }

    /**
     * Get status for a specific file path
     */
    getFileStatus(path: string): FileGitStatus | undefined {
        return this.statusCache.get(path);
    }

    /**
     * Get all modified files
     */
    getModifiedFiles(): FileGitStatus[] {
        return Array.from(this.statusCache.values()).filter(
            f => f.status === 'modified' || f.status === 'added'
        );
    }

    /**
     * Get statistics about current changes
     */
    getStats(): { modified: number; added: number; deleted: number; untracked: number } {
        const files = Array.from(this.statusCache.values());
        return {
            modified: files.filter(f => f.status === 'modified').length,
            added: files.filter(f => f.status === 'added').length,
            deleted: files.filter(f => f.status === 'deleted').length,
            untracked: files.filter(f => f.status === 'untracked').length
        };
    }
}
