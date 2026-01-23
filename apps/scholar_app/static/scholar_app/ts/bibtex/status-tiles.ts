// Toggle panel function for tiles
function toggleBibtexPanel(header: HTMLElement): void {
    const tile = header.closest('.bibtex-tile');
    if (tile) {
        tile.classList.toggle('bibtex-tile--expanded');
    }
}

// Make function globally available
(window as any).toggleBibtexPanel = toggleBibtexPanel;
