/** Owned browser entry: exercise the actual renderers, not substitute engines. */
import { highlightCodeBlocks } from "../../../static/shared/ts/components/_global-ai-chat/markdown-render";
import { appendSvgImage, interactiveSvg } from "../../../static/shared/ts/utils/diagram-svg";
import { renderMermaidContent, showError, showPlaceholder } from "../../../apps/workspace/clew_app/static/clew_app/ts/clew-rendering";
(globalThis as any).diagramHarness = { highlightCodeBlocks, appendSvgImage, interactiveSvg, renderMermaidContent, showError, showPlaceholder };
