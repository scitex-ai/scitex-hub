/**
 * DataTableManager - Re-exported from shared module
 *
 * This file re-exports the shared DataTableManager for backward compatibility.
 * The shared module supports both the legacy constructor signature and the new config-based approach.
 *
 * Legacy usage (vis_app pattern):
 *   new DataTableManager(statusBarCallback, updateColumnDropdownsCallback, updateRulersAreaTransformCallback)
 *
 * New usage:
 *   new DataTableManager({ container: '#my-container', readOnly: false, onDataChange: callback })
 */

export { DataTableManager } from '../../../../../../static/shared/ts/components/data-table/index.js';
