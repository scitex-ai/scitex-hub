/**
 * TreeSyncCoordinator - Handles file tree synchronization
 *
 * Extracted from VisEditor to maintain single responsibility.
 * Manages syncing between canvas/panel selections and the file tree.
 */

export interface TreeSyncCoordinatorDeps {
    getProjectContext: () => { projectOwner: string; projectSlug: string };
}

export class TreeSyncCoordinator {
    private deps: TreeSyncCoordinatorDeps;

    constructor(deps: TreeSyncCoordinatorDeps) {
        this.deps = deps;
    }

    /**
     * Sync file tree to a panel selection
     */
    public syncTreeToPanel(absolutePltzPath: string): void {
        this.syncTreeToPath(absolutePltzPath, 'panel');
    }

    /**
     * Sync file tree to a figure selection
     */
    public syncTreeToFigure(absoluteFigzPath: string): void {
        this.syncTreeToPath(absoluteFigzPath, 'figure');
    }

    /**
     * Sync file tree to an absolute path
     */
    public syncTreeToPath(absolutePath: string, source: string): void {
        const { projectOwner, projectSlug } = this.deps.getProjectContext();
        if (!projectOwner || !projectSlug) return;

        const prefix = `/app/data/users/${projectOwner}/proj/${projectSlug}/`;
        let relativePath = absolutePath;
        if (absolutePath.startsWith(prefix)) {
            relativePath = absolutePath.substring(prefix.length);
        }

        const filesTree = (window as any).filesTree;
        if (filesTree && typeof filesTree.selectFile === 'function') {
            filesTree.selectFile(relativePath, true);
            console.log(`[TreeSyncCoordinator] Synced tree to ${source}: ${relativePath}`);
        }
    }

    /**
     * Refresh the files tree
     */
    public async refreshFilesTree(): Promise<void> {
        const filesTree = (window as any).filesTree;
        if (filesTree && typeof filesTree.refresh === 'function') {
            await filesTree.refresh();
        }
    }
}
