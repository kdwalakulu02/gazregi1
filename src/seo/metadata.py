"""Unique per-page SEO titles and descriptions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageMetadata:
    title: str
    description: str


def _excerpt(text: str, limit: int = 155) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[:limit].rsplit(" ", 1)[0] + "..."


def record_metadata(gazette_no: str, printed_page: int | None, physical_page: int, text: str) -> PageMetadata:
    page_label = f"printed page {printed_page}" if printed_page else f"PDF page {physical_page}"
    title = f"Sri Lanka Gazette No. {gazette_no} - {page_label}"
    description = f"Official Sri Lanka Government Gazette No. {gazette_no}, {page_label}: {_excerpt(text)}"
    return PageMetadata(title=title, description=description)


def issue_metadata(gazette_no: str, publication_date: str, page_count: int) -> PageMetadata:
    title = f"Sri Lanka Gazette No. {gazette_no} ({publication_date}) - {page_count} pages"
    description = (
        f"Browse every searchable page of Sri Lanka Government Gazette No. {gazette_no}, "
        f"published {publication_date}, with links to the official source."
    )
    return PageMetadata(title=title, description=description)


def home_metadata(issue_count: int, page_count: int) -> PageMetadata:
    title = "GazetteRegistry - Search Sri Lanka Government Gazette records"
    description = (
        f"Search {page_count} indexed pages across {issue_count} official Sri Lanka Government Gazette issues "
        "by name, company, tender reference, or topic."
    )
    return PageMetadata(title=title, description=description)
