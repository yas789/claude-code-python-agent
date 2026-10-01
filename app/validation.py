from app.errors import ToolError


def validate_positive_integer(name: str, value: object, maximum: int | None = None) -> None:
    """Require a positive integer, excluding booleans even though they subclass int."""
    if type(value) is not int or value < 1:
        raise ToolError(f"{name} must be a positive integer")
    if maximum is not None and value > maximum:
        raise ToolError(f"{name} must not exceed {maximum}")


def validate_text(name: str, value: object, allow_empty: bool = False) -> None:
    if not isinstance(value, str):
        raise ToolError(f"{name} must be a string")
    if not allow_empty and not value:
        raise ToolError(f"{name} must not be empty")


def validate_path(path: object) -> None:
    validate_text("path", path)
    if "\0" in path:
        raise ToolError("path must not contain null characters")
