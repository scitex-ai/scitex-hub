/**
 * Shell CSS — imported from scitex-ui (canonical source, bundled by Vite).
 *
 * These CSS modules are shared between scitex-cloud and standalone apps.
 * The canonical source is scitex-ui; scitex-cloud imports via Vite alias.
 * Corresponding <link> tags in global_head_styles.html have been removed
 * to prevent double-loading.
 */

// Shell layout
// @ts-ignore
import "scitex-ui/css/shell/stx-shell-sidebar.css";
// @ts-ignore
import "scitex-ui/css/shell/panel-resizer.css";
// workspace-three-col.css removed — replaced by workspace-layout.css + workspace-sidebar.css

// Workspace viewer pane
// @ts-ignore
import "scitex-ui/css/shell/workspace-viewer.css";
// @ts-ignore
import "scitex-ui/css/shell/workspace-viewer-preview.css";

// Workspace files tree
// @ts-ignore
import "scitex-ui/css/shell/workspace-files-tree.css";

// Mobile layout — bottom tab bar removed, sidebar drawer replaces it
// @ts-ignore
import "scitex-ui/css/shell/mobile.css";

// App-level reusable components from scitex-ui
// @ts-ignore
import "scitex-ui/css/app/toggle-switch.css";
// @ts-ignore
import "scitex-ui/css/app/settings-card.css";
// @ts-ignore
import "scitex-ui/css/app/sidebar-layout.css";
// @ts-ignore
import "scitex-ui/css/app/context-menu.css";
