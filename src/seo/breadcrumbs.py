"""Breadcrumb trails shared between page templates and structured data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Crumb:
    label: str
    path: str


def home_crumb() -> Crumb:
    return Crumb("GazetteRegistry", "/")


def issue_breadcrumbs(gazette_no: str, issue_path: str) -> list[Crumb]:
    return [home_crumb(), Crumb(f"Gazette No. {gazette_no}", issue_path)]


def record_breadcrumbs(gazette_no: str, issue_path: str, page_label: str, record_path: str) -> list[Crumb]:
    return [*issue_breadcrumbs(gazette_no, issue_path), Crumb(page_label, record_path)]
