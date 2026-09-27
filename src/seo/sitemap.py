"""Minimal XML sitemap builder (single file; well under the 50,000 URL limit)."""

from __future__ import annotations

import html
from pathlib import Path

from .canonical import canonical_url


class SitemapBuilder:
    def __init__(self) -> None:
        self._paths: list[str] = []

    def add(self, path: str) -> None:
        self._paths.append(path)

    def write(self, output_path: Path) -> None:
        urls = "\n".join(
            f"  <url><loc>{html.escape(canonical_url(path), quote=True)}</loc></url>" for path in self._paths
        )
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}\n"
            "</urlset>\n"
        )
        output_path.write_text(content, encoding="utf-8")
