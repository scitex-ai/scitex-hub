"""Materialize one reviewed source link in image defaults, never runtime mounts."""

import os
import pathlib
import tempfile


def materialize(app_root):
    root = pathlib.Path(app_root)
    source = root / "src/scitex_hub/_cli_audit_dict.yaml"
    target = root / ".scitex/dev/cli-audit-dict.yaml"
    for directory in (
        root,
        source.parent.parent,
        source.parent,
        target.parent.parent,
        target.parent,
    ):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Image vocabulary parents must be real directories")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Canonical image vocabulary must be a regular source file")
    content = source.read_bytes()
    if not target.is_symlink():
        if target.is_file() and target.read_bytes() == content:
            return
        raise ValueError("Image vocabulary is not the reviewed source link or copy")
    if os.readlink(target) != os.path.relpath(source, target.parent):
        raise ValueError("Image vocabulary link does not name the canonical source")
    descriptor, name = tempfile.mkstemp(prefix=".image-vocabulary-", dir=target.parent)
    temporary = pathlib.Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    materialize("/app")
