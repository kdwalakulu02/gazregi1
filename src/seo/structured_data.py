"""JSON-LD structured data builders."""

from __future__ import annotations

import json
from typing import Any

from .breadcrumbs import Crumb
from .canonical import canonical_url


def breadcrumb_list(crumbs: list[Crumb]) -> dict[str, Any]:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": crumb.label,
                "item": canonical_url(crumb.path),
            }
            for index, crumb in enumerate(crumbs)
        ],
    }


def web_page(path: str, title: str, description: str, crumbs: list[Crumb]) -> str:
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": canonical_url(path),
                "url": canonical_url(path),
                "name": title,
                "description": description,
                "isPartOf": {"@type": "WebSite", "name": "GazetteRegistry", "url": canonical_url("/")},
            },
            breadcrumb_list(crumbs),
        ],
    }
    return json.dumps(graph, ensure_ascii=False)


def dataset(issue_count: int, page_count: int) -> str:
    graph = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "GazetteRegistry Sri Lanka Gazette Index",
        "description": (
            f"An independently indexed collection of {page_count} pages across {issue_count} official "
            "Sri Lanka Government Gazette issues, linked to their original source documents."
        ),
        "url": canonical_url("/"),
        "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "GazetteRegistry"},
    }
    return json.dumps(graph, ensure_ascii=False)
