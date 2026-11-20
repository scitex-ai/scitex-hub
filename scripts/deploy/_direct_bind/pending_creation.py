"""Keep owned inputs alive when Docker may still be handling a create request."""

import json
import os


def preserve_pending_creation(target):
    """Record recovery identity without copying environment or deleting resources."""
    owner = json.loads((target.workspace / "owner.json").read_text())
    if owner["token"] != target.token:
        raise ValueError("owned preparation workspace identity changed")
    marker = target.workspace / "pending-creation.json"
    payload = {
        "token": target.token,
        "workspace": str(target.workspace),
        "image": target.image,
        "install_name": target.install_name,
        "probe_name": target.probe_name,
        "volume": target.volume,
        "stage": target.stage,
    }
    if marker.is_symlink():
        raise ValueError("pending preparation descriptor is not a regular file")
    if marker.exists():
        if json.loads(marker.read_text()) != payload:
            raise ValueError("pending preparation descriptor identity changed")
    else:
        fd = os.open(
            marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    return (
        "owned container creation is not yet visible during {0}; retained private "
        "owner state at {1}; no deployment changed"
    ).format(target.stage, marker)
