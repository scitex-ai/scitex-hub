/**
 * Type definitions for SciTeX Vis
 */

export interface JournalPreset {
    id: number;
    name: string;
    column_type: string;
    width_mm: number;
    height_mm: number | null;
    width_px?: number;
    height_px?: number | null;
    dpi: number;
    font_family: string;
    font_size_pt: number;
    line_width_pt: number;
}

export interface PanelLayout {
    rows: number;
    cols: number;
    panels: string[];
}

export interface FigureConfig {
    id: string;
    title: string;
    layout: string;
    canvas_state: any;
    canvas_width_px: number | null;
    canvas_height_px: number | null;
    canvas_dpi: number;
    journal_preset_id: number | null;
}

export interface PanelInfo {
    position: string;
    x: number;
    y: number;
    width: number;
    height: number;
}
