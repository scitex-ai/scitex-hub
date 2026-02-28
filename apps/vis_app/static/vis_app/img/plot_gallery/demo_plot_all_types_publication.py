#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-19 14:08:24 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-code/examples/demo_plot_all_types_publication.py

"""
Publication-ready comprehensive demo suite using the unified style system.

Split into sub-modules:
  _demo_matplotlib_basic  - Matplotlib basic plots (plot, scatter, bar, etc.)
  _demo_custom_scitex     - Custom scitex plots + functional plots
  _demo_seaborn           - Seaborn integration
  _demo_multi_panel       - Multi-panel figures and style override
"""

import matplotlib
import scitex as stx

matplotlib.use("Agg")

from ._demo_custom_scitex import CUSTOM_DEMOS
from ._demo_matplotlib_basic import BASIC_DEMOS
from ._demo_multi_panel import MULTI_DEMOS
from ._demo_seaborn import SEABORN_DEMOS
from ._demo_utils import (
    OUTPUT_DIR,
    OUTPUT_DIR_BASIC,
    OUTPUT_DIR_CUSTOM,
    OUTPUT_DIR_FUNCTIONAL,
    OUTPUT_DIR_MULTI,
    OUTPUT_DIR_SEABORN,
)


@stx.session
def main(verbose=True):
    """Run all publication demos showcasing mm-control integration."""
    if verbose:
        print("\n" + "=" * 70)
        print(" PUBLICATION-READY FIGURE DEMONSTRATION")
        print(" Using Unified Style System")
        print("=" * 70)
        print("\nThis demo showcases scitex.plt.subplots() with mm-control")
        print("integration for creating publication-ready figures.\n")

    demos = BASIC_DEMOS + CUSTOM_DEMOS + SEABORN_DEMOS + MULTI_DEMOS

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n[ERROR] in {demo.__name__}: {e}")
            import traceback

            traceback.print_exc()

    if verbose:
        print("\n" + "=" * 70)
        print(" DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\nOutput locations:")
        print(f"  Session output: {__file__.replace('.py', '_out')}/")
        print(f"  Matplotlib basic: {OUTPUT_DIR_BASIC}/")
        print(f"  Custom scitex: {OUTPUT_DIR_CUSTOM}/")
        print(f"  Functional: {OUTPUT_DIR_FUNCTIONAL}/")
        print(f"  Seaborn: {OUTPUT_DIR_SEABORN}/")
        print(f"  Multi-panels: {OUTPUT_DIR_MULTI}/")
        print(f"  Root (style override): {OUTPUT_DIR}/")
        print("\nCoverage:")
        print("  - Matplotlib basic plots (11): plot, scatter, bar, barh, hist,")
        print("    boxplot, errorbar, fill_between, imshow, contour, violinplot")
        print("  - Custom scitex plots (7): plot_heatmap, plot_line,")
        print("    plot_shaded_line, plot_violin, plot_ecdf, plot_box,")
        print("    plot_mean_std")
        print("  - Functional plots (1): plot_kde")
        print("  - Seaborn integration (8): sns_boxplot, sns_violinplot,")
        print("    sns_scatterplot, sns_lineplot, sns_histplot, sns_barplot,")
        print("    sns_stripplot, sns_kdeplot")
        print("  - Multi-panel (2): 2x2 grid, 1x3 with varied widths")
        print("  - Total: 30 publication-ready plot demonstrations")

    return 0


if __name__ == "__main__":
    main()

# EOF
