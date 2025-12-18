/**
 * TreeMessageHandler - Message notification for file tree
 *
 * Responsibilities:
 * - Show notification messages via SciTeX.notify or custom event
 * - Log messages to console
 *
 * Extracted from WorkspaceFilesTree.ts for single responsibility.
 */

export function showTreeMessage(
    message: string,
    type: "success" | "error" | "info"
): void {
    // Try SciTeX notify first
    if ((window as any).SciTeX?.notify) {
        (window as any).SciTeX.notify(message, type);
        return;
    }

    // Fallback to custom event
    window.dispatchEvent(
        new CustomEvent("wft-message", {
            detail: { message, type },
        })
    );

    // Console logging
    const logMethod =
        type === "error" ? "error" : type === "success" ? "log" : "info";
    console[logMethod](`[WorkspaceFilesTree] ${message}`);
}
