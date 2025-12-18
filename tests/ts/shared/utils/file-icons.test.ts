/**
 * Tests for static/shared/ts/utils/file-icons.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/static/shared/ts/utils/file-icons';

describe('file-icons', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: static/shared/ts/utils/file-icons.ts
// =============================================================================

// /**
//  * Shared File Icons Module
//  * Centralized icon definitions for consistency across all modules
//  * Used by: Files page, Code workspace, and all other file browsers
//  */
// 
// console.log("[DEBUG] /static/shared/ts/utils/file-icons.ts loaded");
// 
// export interface IconConfig {
//   icon: string;
//   color: string;
// }
// 
// /**
//  * Get colorful file icon based on filename/extension
//  */
// export function getFileIcon(fileName: string): string {
//   const ext = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
//   const name = fileName.toLowerCase();
// 
//   // Comprehensive icon map (Gitea-inspired)
//   const iconMap: { [key: string]: IconConfig } = {
//     // Programming languages
//     '.py': { icon: 'fab fa-python', color: '#3776ab' },
//     '.js': { icon: 'fab fa-js', color: '#f7df1e' },
//     '.ts': { icon: 'fab fa-js', color: '#3178c6' },
//     '.jsx': { icon: 'fab fa-react', color: '#61dafb' },
//     '.tsx': { icon: 'fab fa-react', color: '#61dafb' },
//     '.java': { icon: 'fab fa-java', color: '#007396' },
//     '.go': { icon: 'fas fa-code', color: '#00add8' },
//     '.rs': { icon: 'fas fa-gear', color: '#ce422b' },
//     '.c': { icon: 'fas fa-file-code', color: '#555555' },
//     '.cpp': { icon: 'fas fa-file-code', color: '#f34b7d' },
// 
//     // Web
//     '.html': { icon: 'fab fa-html5', color: '#e34c26' },
//     '.css': { icon: 'fab fa-css3-alt', color: '#264de4' },
//     '.scss': { icon: 'fab fa-sass', color: '#cc6699' },
// 
//     // Data & Config
//     '.json': { icon: 'fas fa-brackets-curly', color: '#ffa500' },
//     '.yaml': { icon: 'fas fa-file-code', color: '#cb171e' },
//     '.yml': { icon: 'fas fa-file-code', color: '#cb171e' },
//     '.toml': { icon: 'fas fa-file-code', color: '#9c4121' },
//     '.xml': { icon: 'fas fa-file-code', color: '#e37933' },
//     '.csv': { icon: 'fas fa-table', color: '#217346' },
// 
//     // Documentation
//     '.md': { icon: 'fab fa-markdown', color: '#000000' },
//     '.txt': { icon: 'fas fa-file-alt', color: '#777777' },
//     '.pdf': { icon: 'fas fa-file-pdf', color: '#ff0000' },
//     '.tex': { icon: 'fas fa-file-alt', color: '#3d6117' },
//     '.bib': { icon: 'fas fa-book-open', color: '#cb4b16' },  // BibTeX files
// 
//     // Scripts & Shell
//     '.sh': { icon: 'fas fa-terminal', color: '#89e051' },
//     '.bash': { icon: 'fas fa-terminal', color: '#89e051' },
// 
//     // Data Science
//     '.r': { icon: 'fab fa-r-project', color: '#276dc3' },
//     '.ipynb': { icon: 'fas fa-book', color: '#ff6f00' },
//     '.sql': { icon: 'fas fa-database', color: '#e38c00' },
// 
//     // Images
//     '.jpg': { icon: 'fas fa-image', color: '#00bfa5' },
//     '.jpeg': { icon: 'fas fa-image', color: '#00bfa5' },
//     '.png': { icon: 'fas fa-image', color: '#00bfa5' },
//     '.gif': { icon: 'fas fa-image', color: '#00bfa5' },
//     '.svg': { icon: 'fas fa-image', color: '#ffb300' },
//     '.webp': { icon: 'fas fa-image', color: '#00bfa5' },
// 
//     // Archives
//     '.zip': { icon: 'fas fa-file-archive', color: '#8b8b8b' },
//     '.tar': { icon: 'fas fa-file-archive', color: '#8b8b8b' },
//     '.gz': { icon: 'fas fa-file-archive', color: '#8b8b8b' },
// 
//     // Others
//     '.log': { icon: 'fas fa-file-lines', color: '#777777' },
//     '.env': { icon: 'fas fa-cog', color: '#edb92e' },
//   };
// 
//   // Special file names
//   const specialFiles: { [key: string]: IconConfig } = {
//     'readme.md': { icon: 'fas fa-book', color: '#00b0ff' },
//     'readme': { icon: 'fas fa-book', color: '#00b0ff' },
//     'license': { icon: 'fas fa-scroll', color: '#ffab00' },
//     'dockerfile': { icon: 'fab fa-docker', color: '#2496ed' },
//     'makefile': { icon: 'fas fa-cog', color: '#6d6d6d' },
//     '.gitignore': { icon: 'fab fa-git-alt', color: '#f05032' },
//     '.gitattributes': { icon: 'fab fa-git-alt', color: '#f05032' },
//     'package.json': { icon: 'fab fa-npm', color: '#cb3837' },
//     'tsconfig.json': { icon: 'fab fa-js', color: '#3178c6' },
//     'requirements.txt': { icon: 'fab fa-python', color: '#3776ab' },
//     'setup.py': { icon: 'fab fa-python', color: '#3776ab' },
//   };
// 
//   if (specialFiles[name]) {
//     const { icon, color } = specialFiles[name];
//     return `<i class="${icon}" style="color: ${color}; width: 16px; text-align: center;"></i>`;
//   }
// 
//   if (iconMap[ext]) {
//     const { icon, color } = iconMap[ext];
//     return `<i class="${icon}" style="color: ${color}; width: 16px; text-align: center;"></i>`;
//   }
// 
//   // Default file icon
//   return '<i class="fas fa-file" style="color: #777; width: 16px; text-align: center;"></i>';
// }
// 
// /**
//  * Get folder icon HTML
//  */
// export function getFolderIcon(): string {
//   return '<i class="fas fa-folder" style="color: #dcb67a; width: 16px; text-align: center;"></i>';
// }

// =============================================================================
// End of Source Code
// =============================================================================
