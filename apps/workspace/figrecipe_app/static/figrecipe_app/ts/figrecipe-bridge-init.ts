/**
 * figrecipe bridge shim — delegates to figrecipe package's bridge.
 *
 * This thin wrapper lives in scitex-cloud so the Vite dev server can
 * resolve it via conventional paths. The actual bridge implementation
 * is in the figrecipe repository, resolved via "figrecipe-editor" alias.
 */
import "figrecipe-editor/bridge/bridge-init";
