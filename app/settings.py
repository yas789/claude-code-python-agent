"""Runtime provider settings for the local-first mlab command."""

import os
from dataclasses import dataclass

from openai import OpenAI

LOCAL_BASE_URL = "http://localhost:11434/v1"
LOCAL_MODEL = "granite3.3:2b"


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls):
        return cls(
            base_url=os.getenv("MLAB_BASE_URL")
            or os.getenv("OPENROUTER_BASE_URL")
            or LOCAL_BASE_URL,
            api_key=os.getenv("MLAB_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "ollama",
            model=os.getenv("MLAB_MODEL") or LOCAL_MODEL,
        )

    def create_client(self):
        return OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=120.0, max_retries=0)
