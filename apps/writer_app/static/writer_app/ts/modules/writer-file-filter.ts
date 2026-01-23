/**
 * Writer File Filter - Doctype and Section-based Filtering
 *
 * Filters the file tree based on:
 * - Document type (manuscript/supplementary/revision/shared)
 * - Current section (abstract/introduction/methods/etc.)
 *
 * Rules:
 * - Show only files from the selected doctype directory
 * - Mark files from other sections as disabled (grayed out)
 * - Only .tex files from current section are clickable
 */

export interface WriterFilterState {
    doctype: 'manuscript' | 'supplementary' | 'revision' | 'shared';
    section: string | null;
}

export class WriterFileFilter {
    private state: WriterFilterState;
    private onFilterChange: (() => void) | null = null;

    // Files that should not be editable
    private readonly nonEditableFiles = [
        // Full manuscripts (no preview compilation, show corresponding PDF)
        '01_manuscript/manuscript.tex',
        '02_supplementary/supplementary.tex',
        '03_revision/revision.tex',
        'manuscript.tex',  // Also check without prefix
        'supplementary.tex',
        'revision.tex',

        // Diff manuscripts (no preview compilation, show corresponding PDF)
        '01_manuscript/manuscript_diff.tex',
        '02_supplementary/supplementary_diff.tex',
        '03_revision/revision_diff.tex',
        'manuscript_diff.tex',  // Also check without prefix
        'supplementary_diff.tex',
        'revision_diff.tex',

        // System files - Manuscript
        '01_manuscript/base.tex',
        '01_manuscript/contents/wordcount.tex',

        // System files - Supplementary
        '02_supplementary/base.tex',
        '02_supplementary/contents/wordcount.tex',

        // System files - Revision
        '03_revision/base.tex',
        '03_revision/contents/wordcount.tex',

        // System files - Generic (for non-prefixed paths)
        'base.tex',
        'wordcount.tex',
        'contents/wordcount.tex',
    ];

    constructor(initialDoctype: string = 'manuscript', initialSection: string | null = null) {
        this.state = {
            doctype: initialDoctype as WriterFilterState['doctype'],
            section: initialSection,
        };
    }

    /**
     * Set callback for when filter changes
     */
    public setOnFilterChange(callback: () => void): void {
        this.onFilterChange = callback;
    }

    /**
     * Update document type
     */
    public setDoctype(doctype: string): void {
        this.state.doctype = doctype as WriterFilterState['doctype'];
        this.notifyChange();
    }

    /**
     * Update section
     */
    public setSection(section: string | null): void {
        this.state.section = section;
        this.notifyChange();
    }

    /**
     * Get current filter state
     */
    public getState(): WriterFilterState {
        return { ...this.state };
    }

    /**
     * Get current doctype
     */
    public get currentDocType(): string {
        return this.state.doctype;
    }

    /**
     * Update filter with new doctype and section
     */
    public updateFilter(doctype: string, section: string | null): void {
        this.state.doctype = doctype as WriterFilterState['doctype'];
        this.state.section = section;
        this.notifyChange();
    }

    // System directories that should always be hidden from light users
    private readonly hiddenSystemDirectories = [
        'ai',
        'config',
        'docs',
        'requirements',
        'scripts',
        'tests',
        'texts',
    ];

    /**
     * Check if a file or directory path should be hidden completely
     * Based on doctype - only show selected doctype directory and 00_shared
     * Handles paths with scitex/writer/ prefix
     */
    public shouldHideFile(path: string): boolean {
        const doctype = this.state.doctype;

        // Normalize path - remove scitex/writer/ prefix if present
        let normalizedPath = path;
        if (path.startsWith('scitex/writer/')) {
            normalizedPath = path.replace('scitex/writer/', '');
        }

        // Always show scitex directory (parent) and non-writer subdirectories
        if (path === 'scitex' || path === 'scitex/writer') {
            return false;
        }

        // Hide system directories not relevant to document editing
        for (const hiddenDir of this.hiddenSystemDirectories) {
            if (normalizedPath === hiddenDir || normalizedPath.startsWith(hiddenDir + '/')) {
                return true;
            }
        }

        // Always show 00_shared directory
        if (normalizedPath.startsWith('00_shared') || normalizedPath.startsWith('shared/')) {
            return false;
        }

        // Hide directories that don't match current doctype
        // Check for top-level directories like 01_manuscript, 02_supplementary, 03_revision
        if (normalizedPath.startsWith('01_manuscript')) {
            return doctype !== 'manuscript';
        }
        if (normalizedPath.startsWith('02_supplementary')) {
            return doctype !== 'supplementary';
        }
        if (normalizedPath.startsWith('03_revision')) {
            return doctype !== 'revision';
        }

        // For files in root (not in any doctype dir), keep visible
        return false;
    }

    /**
     * Check if a file should be disabled (grayed out but visible)
     * Based on section - only .tex file from current section is enabled
     */
    public shouldDisableFile(path: string, fileName: string): boolean {
        // Never disable directories
        if (!fileName.includes('.')) {
            return false;
        }

        // Check if file is in the non-editable list
        if (this.isNonEditableFile(path)) {
            return true;
        }

        // If no section selected, don't disable anything else
        if (!this.state.section) {
            return false;
        }

        // Only .tex files are subject to section filtering
        if (!fileName.endsWith('.tex')) {
            return false;
        }

        // Check if this is a compiled PDF section (always show as enabled for viewing)
        if (fileName.includes('compiled_pdf')) {
            return false;
        }

        // Extract section name from filename
        // Expected format: abstract.tex, 01_introduction.tex, etc.
        const baseName = fileName.replace('.tex', '');
        const cleanName = baseName.replace(/^\d+_/, ''); // Remove leading numbers

        // Check if this file matches the current section
        return cleanName !== this.state.section;
    }

    /**
     * Check if a file is in the non-editable list
     */
    private isNonEditableFile(path: string): boolean {
        // Check exact path match
        if (this.nonEditableFiles.includes(path)) {
            return true;
        }

        // Check if the filename (last part of path) matches
        const fileName = path.split('/').pop() || '';
        if (this.nonEditableFiles.includes(fileName)) {
            return true;
        }

        return false;
    }

    /**
     * Check if a file is a full manuscript (no preview compilation)
     */
    public isFullManuscript(path: string): boolean {
        const fullManuscripts = [
            '01_manuscript/manuscript.tex',
            '02_supplementary/supplementary.tex',
            '03_revision/revision.tex',
            'manuscript.tex',
            'supplementary.tex',
            'revision.tex',
        ];

        return fullManuscripts.includes(path) ||
               fullManuscripts.includes(path.split('/').pop() || '');
    }

    /**
     * Check if a file is a diff manuscript (no preview compilation)
     */
    public isDiffManuscript(path: string): boolean {
        const diffManuscripts = [
            '01_manuscript/manuscript_diff.tex',
            '02_supplementary/supplementary_diff.tex',
            '03_revision/revision_diff.tex',
            'manuscript_diff.tex',
            'supplementary_diff.tex',
            'revision_diff.tex',
        ];

        return diffManuscripts.includes(path) ||
               diffManuscripts.includes(path.split('/').pop() || '');
    }

    /**
     * Check if a file should skip preview compilation
     */
    public shouldSkipPreviewCompilation(path: string): boolean {
        return this.isFullManuscript(path) || this.isDiffManuscript(path);
    }

    /**
     * Get the corresponding PDF path for a full/diff manuscript
     * Returns the PDF file that should be displayed when viewing these files
     */
    public getCorrespondingPDF(path: string): string | null {
        // Full manuscripts
        if (path.includes('01_manuscript/manuscript.tex') || path === 'manuscript.tex') {
            return '01_manuscript/manuscript.pdf';
        }
        if (path.includes('02_supplementary/supplementary.tex') || path === 'supplementary.tex') {
            return '02_supplementary/supplementary.pdf';
        }
        if (path.includes('03_revision/revision.tex') || path === 'revision.tex') {
            return '03_revision/revision.pdf';
        }

        // Diff manuscripts
        if (path.includes('01_manuscript/manuscript_diff.tex') || path === 'manuscript_diff.tex') {
            return '01_manuscript/manuscript_diff.pdf';
        }
        if (path.includes('02_supplementary/supplementary_diff.tex') || path === 'supplementary_diff.tex') {
            return '02_supplementary/supplementary_diff.pdf';
        }
        if (path.includes('03_revision/revision_diff.tex') || path === 'revision_diff.tex') {
            return '03_revision/revision_diff.pdf';
        }

        return null;
    }

    /**
     * Check if a file is a system file (base.tex, wordcount.tex)
     */
    public isSystemFile(path: string): boolean {
        return path.includes('base.tex') || path.includes('wordcount.tex');
    }

    /**
     * Get the expected file path for a given doctype and section
     * File structure: scitex/writer/{doctype_dir}/contents/{section}.tex
     * Example: scitex/writer/01_manuscript/contents/abstract.tex
     * Example: scitex/writer/02_supplementary/contents/methods.tex
     */
    public getExpectedFilePath(doctype: string, section: string): string {
        // Map doctype to directory name
        const doctypeDirMap: Record<string, string> = {
            'manuscript': '01_manuscript',
            'supplementary': '02_supplementary',
            'revision': '03_revision',
            'shared': '00_shared',
        };

        const doctypeDir = doctypeDirMap[doctype] || '01_manuscript';

        // For shared, files are directly in the directory
        if (doctype === 'shared') {
            return `scitex/writer/00_shared/${section}.tex`;
        }

        // Standard structure: scitex/writer/{doctype_dir}/contents/{section}.tex
        return `scitex/writer/${doctypeDir}/contents/${section}.tex`;
    }

    /**
     * Extract section name from file path
     */
    public extractSectionFromPath(path: string): string | null {
        // Get filename from path
        const parts = path.split('/');
        const fileName = parts[parts.length - 1];

        if (!fileName.endsWith('.tex')) {
            return null;
        }

        // Remove .tex extension
        const baseName = fileName.replace('.tex', '');

        // Remove leading numbers (e.g., "01_" from "01_introduction")
        const cleanName = baseName.replace(/^\d+_/, '');

        return cleanName;
    }

    /**
     * Notify that filter has changed
     */
    private notifyChange(): void {
        if (this.onFilterChange) {
            this.onFilterChange();
        }
    }
}

// Export singleton instance
let writerFilterInstance: WriterFileFilter | null = null;

export function getWriterFilter(): WriterFileFilter {
    if (!writerFilterInstance) {
        writerFilterInstance = new WriterFileFilter();
    }
    return writerFilterInstance;
}

export function initializeWriterFilter(doctype: string, section: string | null): WriterFileFilter {
    writerFilterInstance = new WriterFileFilter(doctype, section);
    return writerFilterInstance;
}
