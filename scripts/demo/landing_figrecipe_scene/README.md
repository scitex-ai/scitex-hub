# Synthetic FigRecipe landing scene

These three invented examples demonstrate the editor. They are **not MNIST results or research findings**. No training, model calls, or downloads are involved.

Generate with the FigRecipe version recorded in the capture manifest, in an environment with Matplotlib and FigRecipe installed:

```sh
python scripts/demo/landing_figrecipe_scene/generate_examples.py /tmp/landing-figrecipe-example
```

The destination must not exist. The script creates three recipes, their rendered PNGs and data sidecars, plus an example disclaimer. Existing files are never overwritten.

The approved capture uses the real mounted editor's Figures view. Load the three generated recipes using its native recipe-loading action, select Figure 1, then select the Training line. Figure 1/2/3 tabs and the three-item Objects list show the hierarchy. One canvas is visible at a time, following the application's model. Use native zoom controls to fit the plot; the captured view used 98% zoom. Minimize the dock and hide account/project controls before screenshot persistence.

Only native existing-recipe rendering was allowed through `api/switch`; saves, autosaves, model calls and other POSTs were blocked. The screenshot contains an eight-point selected line and its Details. No browser responses, plotted data or application state were replaced. The curves originate in this generator.

`PROVENANCE.json` records the real capture timestamp, image hashes, fixture output hashes and selected artist. The application displayed version 0.44.0 while deployed source declared 0.44.1; the manifest preserves that distinction. The date in the asset filename is the gallery cohort date; the actual UTC capture timestamp is recorded separately.
