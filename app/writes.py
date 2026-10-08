"""Stage encoded edits without opening the destination for writing."""

import os
import stat
import tempfile
from pathlib import Path


def replace_file(path: Path, content: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    staged_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".mlab-edit-", delete=False
        ) as staged:
            staged_path = Path(staged.name)
            staged.write(content)
        staged_path.chmod(mode)
        os.replace(staged_path, path)
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
