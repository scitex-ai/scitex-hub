/** Monaco's vendored-module API over a separate patched DOMPurify instance.
 * Hooks/config belong only to Monaco, never the shared Mermaid/chat sanitizer.
 */
import createDOMPurify from "dompurify";

const purify = createDOMPurify();
export default purify;
export const version = purify.version;
export const isSupported = purify.isSupported;
export const sanitize = purify.sanitize;
export const setConfig = purify.setConfig;
export const clearConfig = purify.clearConfig;
export const isValidAttribute = purify.isValidAttribute;
export const addHook = purify.addHook;
export const removeHook = purify.removeHook;
export const removeHooks = purify.removeHooks;
export const removeAllHooks = purify.removeAllHooks;
