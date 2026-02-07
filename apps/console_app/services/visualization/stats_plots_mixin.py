"""Statistical plot generation methods."""

class StatsPlotsMixin:
    """Mixin for statistical plots (bar, histogram, boxplot, heatmap, violin, pair)."""
    def _generate_bar_plot(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a bar plot."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 6)))

        categories = data.get("categories", [])
        values = data.get("values", [])

        if not categories or not values:
            return False, {"error": "categories and values are required for bar plot"}

        bars = ax.bar(categories, values, color=options.get("color", None))

        ax.set_xlabel(options.get("xlabel", "Categories"))
        ax.set_ylabel(options.get("ylabel", "Values"))
        ax.set_title(options.get("title", "Bar Plot"))

        # Rotate labels if too many categories
        if len(categories) > 10:
            plt.xticks(rotation=45, ha="right")

        # Add value labels on bars if requested
        if options.get("show_values", False):
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height:.1f}",
                    ha="center",
                    va="bottom",
                )

        filename = self._save_figure(fig, "bar_plot")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "bar",
            "categories": len(categories),
        }

    def _generate_histogram(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a histogram."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 6)))

        values = data.get("values", [])

        if not values:
            return False, {"error": "values are required for histogram"}

        bins = options.get("bins", "auto")
        alpha = options.get("alpha", 0.7)

        n, bins, patches = ax.hist(values, bins=bins, alpha=alpha, edgecolor="black")

        ax.set_xlabel(options.get("xlabel", "Values"))
        ax.set_ylabel(options.get("ylabel", "Frequency"))
        ax.set_title(options.get("title", "Histogram"))

        # Add statistics
        if options.get("show_stats", True):
            mean_val = np.mean(values)
            std_val = np.std(values)
            ax.axvline(
                mean_val, color="red", linestyle="--", label=f"Mean: {mean_val:.2f}"
            )
            ax.legend()

        filename = self._save_figure(fig, "histogram")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "histogram",
            "data_points": len(values),
            "bins_count": len(bins) - 1,
        }

    def _generate_boxplot(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a boxplot."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 6)))

        values = data.get("values", [])
        labels = data.get("labels", None)

        if not values:
            return False, {"error": "values are required for boxplot"}

        bp = ax.boxplot(values, labels=labels, patch_artist=True)

        # Color the boxes
        colors = plt.cm.Set3(np.linspace(0, 1, len(values)))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)

        ax.set_ylabel(options.get("ylabel", "Values"))
        ax.set_title(options.get("title", "Box Plot"))

        if options.get("grid", True):
            ax.grid(True, alpha=0.3)

        filename = self._save_figure(fig, "boxplot")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "boxplot",
            "groups": len(values),
        }

    def _generate_heatmap(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a heatmap."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 8)))

        matrix = data.get("matrix", [])

        if not matrix:
            return False, {"error": "matrix data is required for heatmap"}

        # Convert to numpy array if needed
        if isinstance(matrix, list):
            matrix = np.array(matrix)

        cmap = options.get("cmap", "viridis")
        annot = options.get("annotate", True)

        sns.heatmap(
            matrix,
            annot=annot,
            cmap=cmap,
            ax=ax,
            xticklabels=data.get("x_labels", True),
            yticklabels=data.get("y_labels", True),
        )

        ax.set_title(options.get("title", "Heatmap"))

        filename = self._save_figure(fig, "heatmap")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "heatmap",
            "shape": matrix.shape,
        }

    def _generate_violin_plot(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a violin plot."""
        fig, ax = plt.subplots(figsize=options.get("figsize", (10, 6)))

        values = data.get("values", [])
        labels = data.get("labels", None)

        if not values:
            return False, {"error": "values are required for violin plot"}

        vp = ax.violinplot(values, showmeans=True, showmedians=True)

        if labels:
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels)

        ax.set_ylabel(options.get("ylabel", "Values"))
        ax.set_title(options.get("title", "Violin Plot"))

        if options.get("grid", True):
            ax.grid(True, alpha=0.3)

        filename = self._save_figure(fig, "violin_plot")
        plt.close(fig)

        return True, {
            "filename": filename,
            "plot_type": "violin",
            "groups": len(values),
        }

    def _generate_pair_plot(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a pair plot."""
        try:
            # Create DataFrame from data
            df_data = data.get("dataframe", {})
            if not df_data:
                return False, {"error": "dataframe data is required for pair plot"}

            df = pd.DataFrame(df_data)

            # Create pair plot
            g = sns.pairplot(
                df,
                hue=options.get("hue", None),
                diag_kind=options.get("diag_kind", "hist"),
            )

            g.fig.suptitle(options.get("title", "Pair Plot"), y=1.02)

            filename = self._save_figure(g.fig, "pair_plot")
            plt.close(g.fig)

            return True, {
                "filename": filename,
                "plot_type": "pair",
                "variables": len(df.columns),
            }

        except Exception as e:
            return False, {"error": f"Error creating pair plot: {e}"}

# EOF
