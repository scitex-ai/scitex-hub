/** Actual Monaco editor/hover and the plugin-selected sanitizer, no fake engine. */
import * as monaco from "monaco-editor";
import "monaco-editor/min/vs/editor/editor.main.css";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import { renderMarkdown } from "monaco-editor/esm/vs/base/browser/markdownRenderer.js";
import * as sanitizer from "monaco-editor/esm/vs/base/browser/dompurify/dompurify.js";
import shared from "dompurify";
(self as any).MonacoEnvironment = { getWorker: () => new EditorWorker() };
(globalThis as any).monacoHarness = { monaco, renderMarkdown, sanitizer, shared };
