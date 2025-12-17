#!/usr/bin/env python3
"""
SciTeX Icon Viewer - Interactive GUI to browse icon variants.

Usage:
    python scripts/scitex_icon_viewer.py
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import subprocess
import tempfile
import os

# Try to import PIL for image display
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import cairosvg for SVG rendering
try:
    import cairosvg
    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False


ICON_DIR = Path(__file__).parent.parent / "static/shared/images/scitex_logos/scitex-icon/generated"


class IconViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("SciTeX Icon Viewer")
        self.root.geometry("900x700")
        self.root.configure(bg="#1a2a40")

        self.icons = sorted(ICON_DIR.glob("*.svg"))
        self.current_index = 0
        self.preview_size = 300

        self._setup_ui()
        self._load_icon_list()
        if self.icons:
            self._show_icon(0)

    def _setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Icon list
        left_frame = ttk.Frame(main_frame, width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)

        # Search
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._filter_icons)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Icon listbox
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.icon_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            bg="#2d3a4d",
            fg="#ffffff",
            selectbackground="#4a9b7e",
            selectforeground="#ffffff",
        )
        self.icon_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.icon_listbox.yview)
        self.icon_listbox.bind("<<ListboxSelect>>", self._on_select)

        # Count label
        self.count_label = ttk.Label(left_frame, text="")
        self.count_label.pack(pady=(5, 0))

        # Right panel - Preview
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Preview canvas with checkered background
        self.canvas_frame = tk.Frame(right_frame, bg="#333333", width=400, height=400)
        self.canvas_frame.pack(pady=10)
        self.canvas_frame.pack_propagate(False)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            width=self.preview_size,
            height=self.preview_size,
            bg="#333333",
            highlightthickness=0,
        )
        self.canvas.pack(expand=True)

        # Icon name label
        self.name_label = ttk.Label(right_frame, text="", font=("Arial", 11, "bold"))
        self.name_label.pack(pady=5)

        # Info frame
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=10)

        self.info_label = ttk.Label(info_frame, text="", font=("Arial", 10))
        self.info_label.pack()

        # Background selector
        bg_frame = ttk.Frame(right_frame)
        bg_frame.pack(pady=10)

        ttk.Label(bg_frame, text="Preview Background:").pack(side=tk.LEFT)
        self.bg_var = tk.StringVar(value="checker")
        bg_options = ["checker", "white", "black", "gray", "navy", "green"]
        bg_combo = ttk.Combobox(bg_frame, textvariable=self.bg_var, values=bg_options, width=10)
        bg_combo.pack(side=tk.LEFT, padx=(5, 0))
        bg_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_preview())

        # Size slider
        size_frame = ttk.Frame(right_frame)
        size_frame.pack(pady=10)

        ttk.Label(size_frame, text="Size:").pack(side=tk.LEFT)
        self.size_var = tk.IntVar(value=300)
        size_slider = ttk.Scale(
            size_frame,
            from_=100,
            to=500,
            variable=self.size_var,
            orient=tk.HORIZONTAL,
            length=200,
            command=lambda v: self._on_size_change(),
        )
        size_slider.pack(side=tk.LEFT, padx=(5, 0))
        self.size_label = ttk.Label(size_frame, text="300px")
        self.size_label.pack(side=tk.LEFT, padx=(5, 0))

        # Buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Open in Browser", command=self._open_in_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Open Folder", command=self._open_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copy Path", command=self._copy_path).pack(side=tk.LEFT, padx=5)

        # Navigation
        nav_frame = ttk.Frame(right_frame)
        nav_frame.pack(pady=10)

        ttk.Button(nav_frame, text="← Prev", command=self._prev_icon).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Next →", command=self._next_icon).pack(side=tk.LEFT, padx=5)

        # Keyboard bindings
        self.root.bind("<Left>", lambda e: self._prev_icon())
        self.root.bind("<Right>", lambda e: self._next_icon())
        self.root.bind("<Up>", lambda e: self._prev_icon())
        self.root.bind("<Down>", lambda e: self._next_icon())

    def _load_icon_list(self):
        self.icon_listbox.delete(0, tk.END)
        for icon in self.icons:
            name = icon.stem.replace("scitex-icon-", "")
            self.icon_listbox.insert(tk.END, name)
        self.count_label.config(text=f"{len(self.icons)} icons")

    def _filter_icons(self, *args):
        search = self.search_var.get().lower()
        self.icon_listbox.delete(0, tk.END)

        filtered = [i for i in self.icons if search in i.stem.lower()]
        for icon in filtered:
            name = icon.stem.replace("scitex-icon-", "")
            self.icon_listbox.insert(tk.END, name)
        self.count_label.config(text=f"{len(filtered)} / {len(self.icons)} icons")

    def _on_select(self, event):
        selection = self.icon_listbox.curselection()
        if selection:
            idx = selection[0]
            search = self.search_var.get().lower()
            filtered = [i for i in self.icons if search in i.stem.lower()]
            if idx < len(filtered):
                self.current_index = self.icons.index(filtered[idx])
                self._show_icon(self.current_index)

    def _on_size_change(self):
        self.preview_size = self.size_var.get()
        self.size_label.config(text=f"{self.preview_size}px")
        self._refresh_preview()

    def _get_bg_color(self):
        bg = self.bg_var.get()
        colors = {
            "checker": None,
            "white": "#ffffff",
            "black": "#000000",
            "gray": "#6b7280",
            "navy": "#1a2a40",
            "green": "#4a9b7e",
        }
        return colors.get(bg)

    def _draw_checker(self):
        """Draw checkered background for transparency."""
        self.canvas.delete("all")
        size = 20
        colors = ["#cccccc", "#999999"]
        for i in range(0, self.preview_size + size, size):
            for j in range(0, self.preview_size + size, size):
                color = colors[(i // size + j // size) % 2]
                self.canvas.create_rectangle(i, j, i + size, j + size, fill=color, outline="")

    def _show_icon(self, index):
        if not self.icons or index >= len(self.icons):
            return

        icon_path = self.icons[index]
        self.current_index = index

        # Update name
        name = icon_path.stem.replace("scitex-icon-", "")
        self.name_label.config(text=name)

        # Parse info
        parts = name.split("-bg-")
        if len(parts) == 2:
            fill, bg = parts
            self.info_label.config(text=f"Fill: {fill}  |  Background: {bg}")
        else:
            self.info_label.config(text="")

        self._refresh_preview()

    def _refresh_preview(self):
        if not self.icons:
            return

        icon_path = self.icons[self.current_index]

        # Update canvas size
        self.canvas.config(width=self.preview_size, height=self.preview_size)

        # Draw background
        bg_color = self._get_bg_color()
        if bg_color is None:
            self._draw_checker()
        else:
            self.canvas.delete("all")
            self.canvas.config(bg=bg_color)

        # Try to render SVG
        if HAS_PIL and HAS_CAIRO:
            try:
                # Convert SVG to PNG using cairosvg
                png_data = cairosvg.svg2png(
                    url=str(icon_path),
                    output_width=self.preview_size,
                    output_height=self.preview_size,
                )

                # Load with PIL
                import io
                image = Image.open(io.BytesIO(png_data))
                self.photo = ImageTk.PhotoImage(image)

                # Center on canvas
                x = self.preview_size // 2
                y = self.preview_size // 2
                self.canvas.create_image(x, y, image=self.photo, anchor=tk.CENTER)
            except Exception as e:
                self._show_fallback(str(e))
        else:
            self._show_fallback("Install PIL and cairosvg for preview")

    def _show_fallback(self, message):
        """Show fallback message when SVG can't be rendered."""
        self.canvas.delete("all")
        self.canvas.create_text(
            self.preview_size // 2,
            self.preview_size // 2,
            text=f"[SVG Preview]\n\n{message}\n\nClick 'Open in Browser' to view",
            fill="#ffffff",
            font=("Arial", 10),
            justify=tk.CENTER,
        )

    def _prev_icon(self):
        if self.icons:
            self.current_index = (self.current_index - 1) % len(self.icons)
            self._show_icon(self.current_index)
            self._sync_listbox()

    def _next_icon(self):
        if self.icons:
            self.current_index = (self.current_index + 1) % len(self.icons)
            self._show_icon(self.current_index)
            self._sync_listbox()

    def _sync_listbox(self):
        """Sync listbox selection with current index."""
        search = self.search_var.get().lower()
        filtered = [i for i in self.icons if search in i.stem.lower()]
        current_icon = self.icons[self.current_index]

        if current_icon in filtered:
            idx = filtered.index(current_icon)
            self.icon_listbox.selection_clear(0, tk.END)
            self.icon_listbox.selection_set(idx)
            self.icon_listbox.see(idx)

    def _open_in_browser(self):
        if self.icons:
            icon_path = self.icons[self.current_index]
            import webbrowser
            webbrowser.open(f"file://{icon_path}")

    def _open_folder(self):
        subprocess.run(["xdg-open", str(ICON_DIR)], check=False)

    def _copy_path(self):
        if self.icons:
            icon_path = self.icons[self.current_index]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(icon_path))
            self.root.update()


def main():
    if not ICON_DIR.exists():
        print(f"Icon directory not found: {ICON_DIR}")
        print("Run 'python scripts/generate_scitex_icons.py' first")
        return

    root = tk.Tk()

    # Style
    style = ttk.Style()
    style.theme_use("clam")

    app = IconViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
