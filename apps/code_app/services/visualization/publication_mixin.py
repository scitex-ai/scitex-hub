"""Publication figure generation methods."""

class PublicationMixin:
    """Mixin for publication-quality figure generation."""
    def _save_figure(self, fig, plot_type: str) -> str:
        """Save figure to file and return filename."""
        filename = f"{plot_type}_{uuid.uuid4().hex[:8]}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename

        fig.savefig(
            filepath, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
        )

        logger.info(f"Saved visualization: {filepath}")
        return filename

    def generate_publication_figure(
        self, plot_configs: List[Dict[str, Any]], layout: str = "single"
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate publication-ready multi-panel figure."""
        try:
            if layout == "single":
                # Single plot
                if len(plot_configs) != 1:
                    return False, {
                        "error": "Single layout requires exactly one plot config"
                    }

                return self.generate_plot(
                    plot_configs[0]["type"],
                    plot_configs[0]["data"],
                    plot_configs[0].get("options", {}),
                )

            elif layout == "horizontal":
                # Horizontal subplot layout
                fig, axes = plt.subplots(
                    1, len(plot_configs), figsize=(5 * len(plot_configs), 5)
                )
                if len(plot_configs) == 1:
                    axes = [axes]

                filenames = []
                for i, config in enumerate(plot_configs):
                    plt.sca(axes[i])
                    success, result = self._generate_subplot(config, axes[i])
                    if not success:
                        plt.close(fig)
                        return False, result

                plt.tight_layout()
                filename = self._save_figure(fig, "multi_horizontal")
                plt.close(fig)

                return True, {
                    "filename": filename,
                    "plot_type": "multi_horizontal",
                    "subplot_count": len(plot_configs),
                }

            elif layout == "vertical":
                # Vertical subplot layout
                fig, axes = plt.subplots(
                    len(plot_configs), 1, figsize=(8, 4 * len(plot_configs))
                )
                if len(plot_configs) == 1:
                    axes = [axes]

                for i, config in enumerate(plot_configs):
                    plt.sca(axes[i])
                    success, result = self._generate_subplot(config, axes[i])
                    if not success:
                        plt.close(fig)
                        return False, result

                plt.tight_layout()
                filename = self._save_figure(fig, "multi_vertical")
                plt.close(fig)

                return True, {
                    "filename": filename,
                    "plot_type": "multi_vertical",
                    "subplot_count": len(plot_configs),
                }

            else:
                return False, {"error": f"Unsupported layout: {layout}"}

        except Exception as e:
            logger.error(f"Error generating publication figure: {e}")
            return False, {"error": str(e)}

    def _generate_subplot(
        self, config: Dict[str, Any], ax
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a subplot on the given axes."""
        plot_type = config["type"]
        data = config["data"]
        options = config.get("options", {})

        try:
            # Simple subplot generation - can be expanded
            if plot_type == "line":
                x_data = data.get("x", [])
                y_data = data.get("y", [])
                ax.plot(x_data, y_data)
                ax.set_xlabel(options.get("xlabel", "X"))
                ax.set_ylabel(options.get("ylabel", "Y"))
                ax.set_title(options.get("title", ""))

            elif plot_type == "scatter":
                x_data = data.get("x", [])
                y_data = data.get("y", [])
                ax.scatter(x_data, y_data)
                ax.set_xlabel(options.get("xlabel", "X"))
                ax.set_ylabel(options.get("ylabel", "Y"))
                ax.set_title(options.get("title", ""))

            elif plot_type == "bar":
                categories = data.get("categories", [])
                values = data.get("values", [])
                ax.bar(categories, values)
                ax.set_xlabel(options.get("xlabel", "Categories"))
                ax.set_ylabel(options.get("ylabel", "Values"))
                ax.set_title(options.get("title", ""))

            else:
                return False, {"error": f"Subplot type {plot_type} not supported"}

            if options.get("grid", True):
                ax.grid(True, alpha=0.3)

            return True, {"success": True}

        except Exception as e:
            return False, {"error": str(e)}


# EOF
