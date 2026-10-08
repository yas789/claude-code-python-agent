"""Actionable user-facing messages for expected provider failures."""

from urllib.parse import urlparse

from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.diagnostics import clipped


def describe_failure(error, base_url, model):
    endpoint = urlparse(base_url)
    host = endpoint.hostname or "the configured API"
    if isinstance(error, APITimeoutError):
        return "The model request timed out. Try a shorter prompt or a smaller model."
    if isinstance(error, APIConnectionError):
        hint = " Start it with: ollama serve" if endpoint.port == 11434 else " Check the API URL."
        return f"Cannot connect to {host}." + hint
    if isinstance(error, APIStatusError):
        if error.status_code == 404:
            hint = (
                f" Try: ollama pull {model}"
                if endpoint.port == 11434
                else " Check the model name and API URL."
            )
            return f"Model or endpoint not found: {model}." + hint
        if error.status_code in (401, 403):
            return "API authentication failed. Check MLAB_API_KEY and the API URL."
        if error.status_code == 429:
            return "The provider is busy or rate-limited. Try again shortly."
        if error.status_code == 400:
            return (
                "The provider rejected this request. Check that the model supports tools; "
                "try /new for fresh context."
            )
        return f"The provider returned HTTP {error.status_code}. Try again shortly."
    return clipped(str(error), 500)
