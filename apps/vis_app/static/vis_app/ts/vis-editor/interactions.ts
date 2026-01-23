/**
 * Interaction Handlers Module - Re-export from modular structure
 *
 * This file maintains backward compatibility by re-exporting from
 * the new modular structure in ./interactions/
 */

export {
  setupInteractionHandlers,
  type InteractionHandlers,
} from "./interactions/index.ts";
