/**
 * Monaco init — transition shim
 * Re-exports from scitex-ui MonacoLoader. Will be deleted after full migration.
 */

// Side-effect: initializes Monaco globally via scitex-ui
export {
  monaco,
  waitForMonaco,
} from "scitex-ui/ts/app/monaco-editor/_MonacoLoader";
