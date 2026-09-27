"""Canonical URL helpers for the static build."""

from __future__ import annotations

import os

# Override with the real production domain before deploying.
DEFAULT_SITE_URL = "https://gazetteregistry.com"


def site_base_url() -> str:
    return os.environ.get("SITE_URL", DEFAULT_SITE_URL).rstrip("/")


def canonical_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{site_base_url()}{path}"
