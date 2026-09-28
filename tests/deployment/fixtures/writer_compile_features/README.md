# Writer compile feature fixture

This is Hub's smallest deployment-gate project. `config.yaml` opts into Writer's
signature footer, `00_shared/claims.json` registers one claim, and
`01_manuscript/base.tex` invokes that claim through `\vclaim`.

`controls/` are deterministic PDF-text controls for machines without TeX. They
are fed to the actual `scitex-writer/scripts/python/check_compile_artifacts.py`
functions: the positive output has both features, while each negative removes
only one. A TeX-capable integration runner may compile this same project and
replace the controls with `pdftotext` output; these files are not claimed to be
compiled artifacts.
