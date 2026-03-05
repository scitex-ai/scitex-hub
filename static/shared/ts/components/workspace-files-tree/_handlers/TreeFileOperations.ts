/**
 * TreeFileOperations - File operation handlers for workspace files tree
 *
 * Responsibilities:
 * - File download
 * - Symlink creation
 * - Bundle extraction
 *
 * Extracted from WorkspaceFilesTree.ts for single responsibility.
 */

import type { TreeConfig } from "../types";

export class TreeFileOperations {
    constructor(
        private config: TreeConfig,
        private getCsrfToken: () => string,
        private refresh: () => Promise<void>,
        private showMessage: (message: string, type: "success" | "error" | "info") => void,
        private stateManagerExpand: (path: string) => void
    ) {}

    /**
     * Download a file
     */
    downloadFile(filePath: string): void {
        const url = `/${this.config.ownerUsername}/${this.config.projectSlug}/blob/${filePath}?mode=raw`;
        const link = document.createElement("a");
        link.href = url;
        link.download = filePath.split("/").pop() || "download";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * Prompt and create a symlink
     */
    async promptCreateSymlink(sourcePath: string): Promise<void> {
        const parts = sourcePath.split("/");
        const fileName = parts.pop() || sourcePath;
        const parentPath = parts.join("/");
        const symlinkName = `${fileName}.symlink`;
        const targetPath = parentPath ? `${parentPath}/${symlinkName}` : symlinkName;

        try {
            const response = await fetch(
                `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/symlink/`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": this.getCsrfToken(),
                    },
                    body: JSON.stringify({ source: sourcePath, target: targetPath }),
                }
            );

            const data = await response.json();
            if (data.success) {
                this.showMessage(`Created ${symlinkName} - drag to move`, "success");
                await this.refresh();
            } else {
                this.showMessage(`Failed: ${data.error}`, "error");
            }
        } catch {
            this.showMessage("Failed to create symlink", "error");
        }
    }

    /**
     * Extract a bundle (.pltz, .figz, .statsz) to a directory
     */
    async extractBundle(bundlePath: string): Promise<void> {
        const outputPath = bundlePath + ".d";
        const bundleName = bundlePath.split("/").pop() || "bundle";

        try {
            const response = await fetch(
                `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/extract-bundle/`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": this.getCsrfToken(),
                    },
                    body: JSON.stringify({
                        bundle_path: bundlePath,
                        output_path: outputPath,
                    }),
                }
            );

            const data = await response.json();
            if (data.success) {
                this.showMessage(
                    `Extracted ${bundleName} to ${bundleName}.d`,
                    "success"
                );
                await this.refresh();
                this.stateManagerExpand(outputPath);
            } else {
                this.showMessage(`Failed: ${data.error}`, "error");
            }
        } catch (error) {
            console.error("[TreeFileOperations] Failed to extract bundle:", error);
            this.showMessage("Failed to extract bundle", "error");
        }
    }
}
