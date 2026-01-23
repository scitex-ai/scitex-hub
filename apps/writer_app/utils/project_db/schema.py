#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database schema initialization and migrations for ProjectDatabase.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def initialize_schema(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript('''
        -- Figures metadata table
        CREATE TABLE IF NOT EXISTS figures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT NOT NULL,

            -- Metadata
            last_modified REAL NOT NULL,
            thumbnail_path TEXT,

            -- Auto-extracted
            tags TEXT,
            is_referenced INTEGER DEFAULT 0,
            reference_count INTEGER DEFAULT 0,

            -- Discovery info
            source TEXT,
            location TEXT,

            -- Index tracking
            indexed_at REAL NOT NULL,

            UNIQUE(file_path)
        );

        -- Indexes for fast queries
        CREATE INDEX IF NOT EXISTS idx_file_hash ON figures(file_hash);
        CREATE INDEX IF NOT EXISTS idx_last_modified ON figures(last_modified);
        CREATE INDEX IF NOT EXISTS idx_is_referenced ON figures(is_referenced);
        CREATE INDEX IF NOT EXISTS idx_source ON figures(source);
        CREATE INDEX IF NOT EXISTS idx_file_type ON figures(file_type);

        -- LaTeX references tracking
        CREATE TABLE IF NOT EXISTS latex_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            figure_id INTEGER NOT NULL,
            tex_file TEXT NOT NULL,
            line_number INTEGER,
            context TEXT,
            FOREIGN KEY (figure_id) REFERENCES figures(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_latex_ref_figure ON latex_references(figure_id);

        -- Full-text search (FTS5)
        CREATE VIRTUAL TABLE IF NOT EXISTS figures_fts USING fts5(
            file_name,
            location,
            tags,
            content='figures',
            content_rowid='id'
        );

        -- Trigger to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS figures_fts_insert AFTER INSERT ON figures BEGIN
            INSERT INTO figures_fts(rowid, file_name, location, tags)
            VALUES (new.id, new.file_name, new.location, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS figures_fts_update AFTER UPDATE ON figures BEGIN
            UPDATE figures_fts SET file_name = new.file_name, location = new.location, tags = new.tags
            WHERE rowid = new.id;
        END;

        CREATE TRIGGER IF NOT EXISTS figures_fts_delete AFTER DELETE ON figures BEGIN
            DELETE FROM figures_fts WHERE rowid = old.id;
        END;

        -- Tables metadata table (similar to figures)
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            caption TEXT,

            -- Metadata
            last_modified REAL NOT NULL,
            thumbnail_path TEXT,

            -- Auto-extracted
            tags TEXT,
            is_referenced INTEGER DEFAULT 0,
            reference_count INTEGER DEFAULT 0,

            -- Discovery info
            source TEXT,
            location TEXT,

            -- Index tracking
            indexed_at REAL NOT NULL,

            UNIQUE(file_path)
        );

        CREATE INDEX IF NOT EXISTS idx_table_is_referenced ON tables(is_referenced);
        CREATE INDEX IF NOT EXISTS idx_table_source ON tables(source);
    ''')


def run_migrations(conn: sqlite3.Connection):
    """Run database migrations for schema updates."""
    # Migration: Add thumbnail_path to tables (2025-01-14)
    try:
        conn.execute('SELECT thumbnail_path FROM tables LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        conn.execute('ALTER TABLE tables ADD COLUMN thumbnail_path TEXT')
        logger.info("[ProjectDB] Migration: Added thumbnail_path column to tables")


# EOF
