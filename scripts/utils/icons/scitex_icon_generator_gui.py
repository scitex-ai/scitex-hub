#!/usr/bin/env python3
"""
SciTeX Icon Generator GUI - Simple and intuitive icon generator with DearPyGui.

Usage:
    python scripts/scitex_icon_generator_gui.py

Requirements:
    pip install dearpygui Pillow cairosvg
"""

import tempfile
import webbrowser
from pathlib import Path
import sys

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    print("Install: pip install dearpygui")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
    import cairosvg
    import io
    HAS_RENDER = True
except ImportError:
    HAS_RENDER = False
    print("For preview: pip install Pillow cairosvg")

sys.path.insert(0, str(Path(__file__).parent))
from generate_scitex_icons import COLORS, SNAKE_PATHS

OUTPUT_DIR = Path(__file__).parent.parent / "static/shared/images/scitex_logos/scitex-icon/generated"
PREVIEW_SIZE = 350

# Color palette
COLOR_OPTIONS = {
    "White": "#ffffff",
    "Black": "#000000",
    "Navy": "#1a2a40",
    "Navy Mid": "#34495e",
    "Green": "#4a9b7e",
    "Slate": "#506b7a",
    "Steel": "#6c8ba0",
    "Gray Light": "#d1d5db",
    "Gray": "#6b7280",
    "Gray Dark": "#374151",
}

# Camo palettes
CAMO_PALETTES = {
    "Forest": ("#4a5d23", "#3d4f1e", "#2d3a16", "#5a6f2a"),
    "Navy": ("#1a2a40", "#263850", "#34495e", "#1e3a5f"),
    "Desert": ("#c2a678", "#a08050", "#8b7355", "#d4c4a8"),
    "Arctic": ("#e8e8e8", "#c0c0c0", "#ffffff", "#d0d0d0"),
    "Urban": ("#4a4a4a", "#606060", "#3a3a3a", "#707070"),
    "Gray": ("#6b7280", "#4b5563", "#9ca3af", "#374151"),
}


class IconGenerator:
    def __init__(self):
        # Snake settings
        self.snake_color = "#ffffff"
        self.snake_camo_enabled = False
        self.snake_camo_style = "Forest"

        # Background settings
        self.bg_color = "#1a2a40"
        self.bg_transparent = False
        self.bg_camo_enabled = False
        self.bg_camo_style = "Forest"

        # Text settings
        self.text_enabled = False
        self.text_content = "scitex.ai"
        self.text_color = "#ffffff"
        self.text_position = "bottom"  # bottom, center, top

        self.texture_tag = None

    def generate_svg(self):
        """Generate SVG based on current settings."""
        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg id="scitex-logo" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2160 2160">',
        ]

        # Determine snake fill
        if self.snake_camo_enabled:
            colors = CAMO_PALETTES[self.snake_camo_style]
            svg_parts.append('  <defs>')
            svg_parts.append('    <pattern id="snake-camo" patternUnits="userSpaceOnUse" width="200" height="200">')
            svg_parts.append(f'      <rect width="200" height="200" fill="{colors[0]}"/>')
            svg_parts.append(f'      <ellipse cx="50" cy="30" rx="60" ry="40" fill="{colors[1]}"/>')
            svg_parts.append(f'      <ellipse cx="150" cy="80" rx="50" ry="35" fill="{colors[2]}"/>')
            svg_parts.append(f'      <ellipse cx="30" cy="120" rx="45" ry="30" fill="{colors[3]}"/>')
            svg_parts.append(f'      <ellipse cx="120" cy="160" rx="55" ry="38" fill="{colors[1]}"/>')
            svg_parts.append('    </pattern>')
            svg_parts.append('  </defs>')
            snake_fill = 'url(#snake-camo)'
        else:
            snake_fill = self.snake_color

        # Determine background
        if not self.bg_transparent:
            if self.bg_camo_enabled:
                colors = CAMO_PALETTES[self.bg_camo_style]
                if not self.snake_camo_enabled:
                    svg_parts.append('  <defs>')
                svg_parts.append('    <pattern id="bg-camo" patternUnits="userSpaceOnUse" width="200" height="200">')
                svg_parts.append(f'      <rect width="200" height="200" fill="{colors[0]}"/>')
                svg_parts.append(f'      <ellipse cx="50" cy="30" rx="60" ry="40" fill="{colors[1]}"/>')
                svg_parts.append(f'      <ellipse cx="150" cy="80" rx="50" ry="35" fill="{colors[2]}"/>')
                svg_parts.append(f'      <ellipse cx="30" cy="120" rx="45" ry="30" fill="{colors[3]}"/>')
                svg_parts.append(f'      <ellipse cx="120" cy="160" rx="55" ry="38" fill="{colors[1]}"/>')
                svg_parts.append('    </pattern>')
                if not self.snake_camo_enabled:
                    svg_parts.append('  </defs>')
                svg_parts.append('  <circle cx="1080" cy="1080" r="1080" fill="url(#bg-camo)"/>')
            else:
                svg_parts.append(f'  <circle cx="1080" cy="1080" r="1080" fill="{self.bg_color}"/>')

        # Add snake
        svg_parts.append('  <g>')
        for path in SNAKE_PATHS:
            svg_parts.append(f'    <path fill="{snake_fill}" d="{path}"/>')
        svg_parts.append('  </g>')

        # Add text if enabled
        if self.text_enabled and self.text_content:
            y_pos = {"top": 400, "center": 1080, "bottom": 1800}[self.text_position]
            svg_parts.append(f'  <text x="1080" y="{y_pos}" text-anchor="middle" ')
            svg_parts.append(f'        font-family="Arial, sans-serif" font-size="180" font-weight="bold" ')
            svg_parts.append(f'        fill="{self.text_color}">{self.text_content}</text>')

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def svg_to_texture(self, svg_content):
        """Convert SVG to DearPyGui texture."""
        if not HAS_RENDER:
            return None
        try:
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode(),
                output_width=PREVIEW_SIZE,
                output_height=PREVIEW_SIZE,
            )
            image = Image.open(io.BytesIO(png_data)).convert("RGBA")

            # Add checkered background for transparency
            if self.bg_transparent:
                checker = Image.new("RGBA", (PREVIEW_SIZE, PREVIEW_SIZE))
                draw = ImageDraw.Draw(checker)
                size = 20
                for i in range(0, PREVIEW_SIZE, size):
                    for j in range(0, PREVIEW_SIZE, size):
                        color = (80, 80, 80) if ((i // size) + (j // size)) % 2 == 0 else (50, 50, 50)
                        draw.rectangle([i, j, i + size, j + size], fill=color)
                checker.paste(image, (0, 0), image)
                image = checker

            pixels = list(image.getdata())
            flat_data = []
            for pixel in pixels:
                flat_data.extend([c / 255.0 for c in pixel])
            return flat_data
        except Exception as e:
            print(f"Render error: {e}")
            return None

    def update_preview(self):
        """Update the preview image."""
        svg_content = self.generate_svg()
        flat_data = self.svg_to_texture(svg_content)

        if flat_data:
            if self.texture_tag and dpg.does_item_exist(self.texture_tag):
                dpg.set_value(self.texture_tag, flat_data)
            else:
                with dpg.texture_registry():
                    self.texture_tag = dpg.add_dynamic_texture(
                        width=PREVIEW_SIZE, height=PREVIEW_SIZE,
                        default_value=flat_data
                    )
                if dpg.does_item_exist("preview_image"):
                    dpg.configure_item("preview_image", texture_tag=self.texture_tag)

        # Update filename
        self._update_filename()

    def _update_filename(self):
        """Update the filename display."""
        parts = ["scitex-icon"]

        # Snake part
        if self.snake_camo_enabled:
            parts.append(f"camo-{self.snake_camo_style.lower()}")
        else:
            for name, hex_val in COLOR_OPTIONS.items():
                if hex_val == self.snake_color:
                    parts.append(name.lower().replace(" ", "-"))
                    break

        parts.append("bg")

        # Background part
        if self.bg_transparent:
            parts.append("transparent")
        elif self.bg_camo_enabled:
            parts.append(f"camo-{self.bg_camo_style.lower()}")
        else:
            for name, hex_val in COLOR_OPTIONS.items():
                if hex_val == self.bg_color:
                    parts.append(name.lower().replace(" ", "-"))
                    break

        filename = "-".join(parts) + ".svg"
        if dpg.does_item_exist("filename_label"):
            dpg.set_value("filename_label", filename)

    def save_to_project(self):
        """Save to project folder."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename
        self._update_filename()
        filename = dpg.get_value("filename_label")
        filepath = OUTPUT_DIR / filename

        svg_content = self.generate_svg()
        filepath.write_text(svg_content)

        # Show confirmation
        print(f"Saved: {filepath}")

    def open_browser(self):
        """Open in browser."""
        svg_content = self.generate_svg()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            webbrowser.open(f"file://{f.name}")


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_color_picker(label, default_color, callback, tag_prefix):
    """Create a color picker row."""
    with dpg.group(horizontal=True):
        dpg.add_text(f"{label}:", color=(200, 200, 200))

        for name, hex_val in COLOR_OPTIONS.items():
            rgb = hex_to_rgb(hex_val)
            with dpg.theme() as btn_theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (*rgb, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*rgb, 200))

            btn = dpg.add_button(
                label="", width=25, height=25,
                callback=callback,
                user_data=hex_val,
                tag=f"{tag_prefix}_{name}"
            )
            dpg.bind_item_theme(btn, btn_theme)
            with dpg.tooltip(btn):
                dpg.add_text(name)


def main():
    gen = IconGenerator()

    dpg.create_context()
    dpg.create_viewport(title="SciTeX Icon Generator", width=750, height=700)

    # Callbacks
    def on_snake_color(sender, app_data, user_data):
        gen.snake_color = user_data
        gen.update_preview()

    def on_snake_camo_toggle(sender, app_data):
        gen.snake_camo_enabled = app_data
        gen.update_preview()

    def on_snake_camo_style(sender, app_data):
        gen.snake_camo_style = app_data
        gen.update_preview()

    def on_bg_color(sender, app_data, user_data):
        gen.bg_color = user_data
        gen.update_preview()

    def on_bg_transparent(sender, app_data):
        gen.bg_transparent = app_data
        gen.update_preview()

    def on_bg_camo_toggle(sender, app_data):
        gen.bg_camo_enabled = app_data
        gen.update_preview()

    def on_bg_camo_style(sender, app_data):
        gen.bg_camo_style = app_data
        gen.update_preview()

    def on_text_toggle(sender, app_data):
        gen.text_enabled = app_data
        gen.update_preview()

    def on_text_content(sender, app_data):
        gen.text_content = app_data
        gen.update_preview()

    def on_text_color(sender, app_data, user_data):
        gen.text_color = user_data
        gen.update_preview()

    def on_text_position(sender, app_data):
        gen.text_position = app_data.lower()
        gen.update_preview()

    # Main window
    with dpg.window(tag="main", label="SciTeX Icon Generator"):
        with dpg.group(horizontal=True):
            # LEFT PANEL - Settings
            with dpg.child_window(width=350, height=-1):

                # === SNAKE SETTINGS ===
                dpg.add_text("SNAKE", color=(100, 200, 150))
                dpg.add_separator()

                dpg.add_spacer(height=5)
                create_color_picker("Color", "#ffffff", on_snake_color, "snake_color")

                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Use Camo Pattern", callback=on_snake_camo_toggle)
                    dpg.add_combo(
                        items=list(CAMO_PALETTES.keys()),
                        default_value="Forest",
                        width=100,
                        callback=on_snake_camo_style
                    )

                dpg.add_spacer(height=20)

                # === BACKGROUND SETTINGS ===
                dpg.add_text("BACKGROUND", color=(100, 200, 150))
                dpg.add_separator()

                dpg.add_spacer(height=5)
                dpg.add_checkbox(label="Transparent", callback=on_bg_transparent)

                dpg.add_spacer(height=5)
                create_color_picker("Color", "#1a2a40", on_bg_color, "bg_color")

                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Use Camo Pattern", callback=on_bg_camo_toggle)
                    dpg.add_combo(
                        items=list(CAMO_PALETTES.keys()),
                        default_value="Forest",
                        width=100,
                        callback=on_bg_camo_style
                    )

                dpg.add_spacer(height=20)

                # === TEXT SETTINGS ===
                dpg.add_text("TEXT (Optional)", color=(100, 200, 150))
                dpg.add_separator()

                dpg.add_spacer(height=5)
                dpg.add_checkbox(label="Add Text", callback=on_text_toggle)

                dpg.add_spacer(height=5)
                with dpg.group(horizontal=True):
                    dpg.add_text("Text:", color=(150, 150, 150))
                    dpg.add_input_text(
                        default_value="scitex.ai",
                        width=150,
                        callback=on_text_content
                    )

                dpg.add_spacer(height=5)
                with dpg.group(horizontal=True):
                    dpg.add_text("Position:", color=(150, 150, 150))
                    dpg.add_combo(
                        items=["Top", "Center", "Bottom"],
                        default_value="Bottom",
                        width=100,
                        callback=on_text_position
                    )

                dpg.add_spacer(height=5)
                create_color_picker("Text Color", "#ffffff", on_text_color, "text_color")

                dpg.add_spacer(height=20)

                # === ACTIONS ===
                dpg.add_text("ACTIONS", color=(100, 200, 150))
                dpg.add_separator()

                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Save to Project", width=150, height=30, callback=gen.save_to_project)
                    dpg.add_button(label="Open in Browser", width=150, height=30, callback=gen.open_browser)

            # RIGHT PANEL - Preview
            with dpg.child_window(width=-1, height=-1):
                dpg.add_text("PREVIEW", color=(100, 200, 150))
                dpg.add_separator()

                dpg.add_spacer(height=10)

                # Placeholder texture
                placeholder = [0.2, 0.2, 0.2, 1.0] * (PREVIEW_SIZE * PREVIEW_SIZE)
                with dpg.texture_registry():
                    dpg.add_dynamic_texture(
                        width=PREVIEW_SIZE, height=PREVIEW_SIZE,
                        default_value=placeholder, tag="preview_texture"
                    )

                dpg.add_image(texture_tag="preview_texture", tag="preview_image")

                dpg.add_spacer(height=10)
                dpg.add_text("", tag="filename_label", color=(150, 200, 150))

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main", True)

    # Initial render
    gen.update_preview()

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
