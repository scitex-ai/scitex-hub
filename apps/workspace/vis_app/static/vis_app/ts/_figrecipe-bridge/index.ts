/** figrecipe-bridge — barrel export. */

export {
  mountFigrecipeEditor,
  unmountFigrecipeEditor,
  switchRecipeFile,
} from "./FigrecipeMountPoint";
export type { MountOptions } from "./FigrecipeMountPoint";

export { emitBridgeEvent, onBridgeEvent } from "./BridgeEventBus";
export type { BridgeEventMap, BridgeEventName } from "./BridgeEventBus";

export {
  wireVisEditorBridge,
  unwireVisEditorBridge,
  runStatAndRenderBracket,
} from "./VisEditorBridge";
