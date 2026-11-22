"""Secrets from the environment or ~/.config/compass/secrets.env, never from the repo."""

import os
from pathlib import Path

SECRETS_FILE = Path(os.environ.get("COMPASS_SECRETS", "~/.config/compass/secrets.env")).expanduser()


def secret(name: str) -> str | None:
    """A secret by name: the environment wins over the file."""
    if name in os.environ:
        return os.environ[name]
    if not SECRETS_FILE.exists():
        return None
    for line in SECRETS_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == name:
            return value.strip()
    return None
