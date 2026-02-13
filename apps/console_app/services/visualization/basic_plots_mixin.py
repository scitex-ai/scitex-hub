"""Basic plot generation methods."""

class BasicPlotsMixin:
    """Mixin for basic plot types (line, scatter, bar)."""
    def _generate_line_plot(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a line plot."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 6)))

        x_data = data.get("x", [])
        y_data = data.get("y", [])

        if not x_data or not y_data:
            return False, {"error": "x and y data are required for line plot"}

        # Multiple series support
        if isinstance(y_data[0], list):
            for i, y_series in enumerate(y_data):
                label = (
                    data.get("labels", [f"Series {i + 1}"])[i]
                    if i < len(data.get("labels", []))
                    else f"Series {i + 1}"
                )
                ax.plot(
                    x_data, y_series, label=label, linewidth=options.get("linewidth", 2)
                )
            ax.legend()
        else:
            ax.plot(x_data, y_data, linewidth=options.get("linewidth", 2))

        ax.set_xlabel(options.get("xlabel", "X"))
        ax.set_ylabel(options.get("ylabel", "Y"))
        ax.set_title(options.get("title", "Line Plot"))

        if options.get("grid", True):
            ax.grid(True, alpha=0.3)

        filename = self._save_figure(fig, "line_plot")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "line",
            "data_points": len(x_data),
        }

    def _generate_scatter_plot(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a scatter plot."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 6)))

        x_data = data.get("x", [])
        y_data = data.get("y", [])

        if not x_data or not y_data:
            return False, {"error": "x and y data are required for scatter plot"}

        # Color and size support
        c = data.get("color", None)
        s = data.get("size", options.get("markersize", 50))

        scatter = ax.scatter(x_data, y_data, c=c, s=s, alpha=options.get("alpha", 0.7))

        # Add colorbar if color data provided
        if c is not None:
            plt.colorbar(scatter, ax=ax, label=options.get("color_label", "Color"))

        ax.set_xlabel(options.get("xlabel", "X"))
        ax.set_ylabel(options.get("ylabel", "Y"))
        ax.set_title(options.get("title", "Scatter Plot"))

        if options.get("grid", True):
            ax.grid(True, alpha=0.3)

        filename = self._save_figure(fig, "scatter_plot")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "scatter",
            "data_points": len(x_data),
        }

# EOF
