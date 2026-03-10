/**
 * Clew drop target + file selection handlers
 */

import { clewApi } from "./api-client";
import {
  fetchFileContent,
  renderImageFile,
  renderMermaidContent,
  showError,
  showLoading,
  getStatusBadge,
} from "./clew-rendering";

export function extractDropPaths(e: DragEvent): string[] {
  // Try scitex-specific format first
  const jsonData = e.dataTransfer?.getData("application/x-scitex-file");
  if (jsonData) {
    try {
      const parsed = JSON.parse(jsonData);
      if (Array.isArray(parsed)) return parsed.map((p: any) => p.path || p);
      if (parsed.path) return [parsed.path];
    } catch {
      /* fall through */
    }
  }
  // Fallback: semicolon-separated paths in text/plain
  const textData = e.dataTransfer?.getData("text/plain");
  if (textData) return textData.split(";").filter(Boolean);
  return [];
}

export async function renderMultiTargetDag(
  dagArea: HTMLElement,
  paths: string[],
) {
  showLoading(dagArea);
  const response = await clewApi.getMermaidDag({
    targetFiles: paths,
    pathMode: "name",
  });

  if (response.success && response.data?.mermaid) {
    await renderMermaidContent(dagArea, response.data.mermaid);
  } else {
    showError(
      dagArea,
      response.error || `No verification data for ${paths.length} files`,
    );
  }
}

export async function handleFileSelected(
  dagArea: HTMLElement,
  filePath: string,
  projectId: string | null,
  detailsPanel: HTMLElement | null,
) {
  // If the file itself is .mmd, render it directly
  if (filePath.endsWith(".mmd")) {
    const content = await fetchFileContent(filePath, projectId);
    if (content) {
      await renderMermaidContent(dagArea, content);
    } else {
      showError(dagArea, `Could not load ${filePath}`);
    }
    return;
  }

  // Look for companion clew files
  const mmdContent = await fetchFileContent(`${filePath}-clew.mmd`, projectId);
  if (mmdContent) {
    await renderMermaidContent(dagArea, mmdContent);
    return;
  }

  const pngCompanion = `${filePath}-clew.png`;
  const pngContent = await fetchFileContent(pngCompanion, projectId);
  if (pngContent !== null) {
    renderImageFile(dagArea, pngCompanion, projectId);
    return;
  }

  // Try clew API chain verification
  const stats = await clewApi.getStats();
  if (stats.success && stats.data && stats.data.total_runs > 0) {
    await loadChainForFile(dagArea, filePath, detailsPanel);
    return;
  }

  console.log("[Clew] No companion files or runs for:", filePath);
}

async function loadChainForFile(
  dagArea: HTMLElement,
  filePath: string,
  detailsPanel: HTMLElement | null,
) {
  showLoading(dagArea);

  const response = await clewApi.verifyChain(filePath);
  if (response.success && response.data) {
    const dagResp = await clewApi.getMermaidDag({
      targetFile: filePath,
      pathMode: "name",
    });
    if (dagResp.success && dagResp.data?.mermaid) {
      await renderMermaidContent(dagArea, dagResp.data.mermaid);
    }
    showChainDetails(detailsPanel, response.data);
  } else {
    showError(dagArea, response.error || "Failed to load verification chain");
  }
}

function showChainDetails(detailsPanel: HTMLElement | null, chainData: any) {
  if (!detailsPanel) return;

  let html = `
    <div class="chain-details">
      <h4>Verification Chain</h4>
      <p><strong>Target:</strong> ${chainData.target_file}</p>
      <p><strong>Status:</strong> ${getStatusBadge(chainData.status)}</p>
      <p><strong>Runs:</strong> ${chainData.runs.length}</p>
    </div>
  `;

  html += '<div class="runs-list">';
  chainData.runs.forEach((run: any, index: number) => {
    html += `
      <div class="run-item">
        <h5>Run ${index + 1}: ${run.session_id.substring(0, 12)}...</h5>
        <p><strong>Script:</strong> ${run.script_path || "Unknown"}</p>
        <p><strong>Status:</strong> ${getStatusBadge(run.status)}</p>
        <p><strong>Files:</strong> ${run.files.length}</p>
      </div>
    `;
  });
  html += "</div>";
  detailsPanel.innerHTML = html;
}
