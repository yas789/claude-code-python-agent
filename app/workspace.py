from dataclasses import dataclass
from pathlib import Path

from app.errors import ToolError


@dataclass(frozen=True)
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).resolve())

    def resolve_path(self, path: str, path_type: str) -> Path:
        resolved = (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            raise ToolError(f"{path_type} is outside workspace: {path}")
        return resolved

    def resolve_file(self, path: str) -> Path:
        return self.resolve_path(path, "file")

    def resolve_directory(self, path: str) -> Path:
        return self.resolve_path(path, "directory")
