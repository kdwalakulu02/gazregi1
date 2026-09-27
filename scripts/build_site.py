"""Validate extracted Gazette records and generate the static search site."""

from __future__ import annotations

import gzip
import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, HttpUrl, PositiveInt

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "lk"
SOURCE_ROOT = ROOT / "src"
OUTPUT_ROOT = ROOT / "dist"

sys.path.insert(0, str(SOURCE_ROOT))

from seo.breadcrumbs import Crumb, home_crumb, issue_breadcrumbs, record_breadcrumbs  # noqa: E402
from seo.canonical import canonical_url  # noqa: E402
from seo.metadata import home_metadata, issue_metadata, record_metadata  # noqa: E402
from seo.sitemap import SitemapBuilder  # noqa: E402
from seo.structured_data import dataset, web_page  # noqa: E402


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl | None
    gazette_no: str
    page_start: int | None
    page_end: int | None
    language: str | None


class GazettePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uid: str
    issue_id: str
    physical_pdf_page: PositiveInt
    printed_page: PositiveInt | None
    section: str | None
    category: str
    subcategory: str | None
    title: str
    summary: str | None
    keywords: list[str]
    source: SourceRecord


class GazetteIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    country: str
    gazette_no: str
    gazette_type: str
    edition: str
    publication_date: date
    source_url: HttpUrl | None
    source_file: str
    page_count: PositiveInt
    parser_version: str
    extraction_method: str
    extracted_at: str


def build_site() -> int:
    issue_dirs = sorted(DATA_ROOT.glob("*/*"))
    if not issue_dirs:
        raise ValueError("No extracted issues found under data/lk/")

    issues: list[tuple[GazetteIssue, list[GazettePage], dict[str, str]]] = []
    seen_uids: set[str] = set()
    for issue_dir in issue_dirs:
        issue_data = json.loads((issue_dir / "issue.json").read_text(encoding="utf-8"))
        issue = GazetteIssue.model_validate(issue_data)
        pages = [
            GazettePage.model_validate(json.loads(line))
            for line in (issue_dir / "pages.ndjson").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        with gzip.open(issue_dir / "text.jsonl.gz", "rt", encoding="utf-8") as source:
            text_records = [json.loads(line) for line in source if line.strip()]
        page_texts = {record["uid"]: record["text"] for record in text_records}
        if len(pages) != len(page_texts):
            raise ValueError(f"Page/text count mismatch for {issue.issue_id}")

        for page in pages:
            if page.issue_id != issue.issue_id or page.uid in seen_uids or page.uid not in page_texts:
                raise ValueError(f"Invalid or duplicate page record: {page.uid}")
            seen_uids.add(page.uid)
        issues.append((issue, pages, page_texts))

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    assets_dir = OUTPUT_ROOT / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for asset in (SOURCE_ROOT / "assets").iterdir():
        shutil.copy2(asset, assets_dir / asset.name)

    sitemap = SitemapBuilder()
    sitemap.add("/")

    all_pages = [(issue, page, texts[page.uid]) for issue, pages, texts in issues for page in pages]
    for issue, page, text in all_pages:
        _write_record_page(issue, page, text, sitemap)
    for issue, pages, texts in issues:
        _write_issue_page(issue, pages, texts, sitemap)

    newest_issue = issues[-1][0]
    issue_page_count = sum(len(pages) for _, pages, _ in issues)
    sample_cards = "\n".join(_sample_card(issue, page, text) for issue, page, text in all_pages[:4])
    source_status = (
        "Official PDF URL recorded."
        if newest_issue.source_url
        else "Official PDF URL not yet recorded for this issue."
    )
    seo = home_metadata(len(issues), issue_page_count)
    home = (SOURCE_ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    replacements = {
        "{{GAZETTE_NUMBER}}": html.escape(newest_issue.gazette_no),
        "{{PUBLICATION_DATE}}": newest_issue.publication_date.strftime("%d %B %Y"),
        "{{PAGE_COUNT}}": str(issue_page_count),
        "{{ISSUE_COUNT}}": str(len(issues)),
        "{{EDITION}}": html.escape(newest_issue.edition),
        "{{SOURCE_STATUS}}": html.escape(source_status),
        "{{SAMPLE_CARDS}}": sample_cards,
        "{{PAGE_TITLE}}": html.escape(seo.title),
        "{{PAGE_DESCRIPTION}}": html.escape(seo.description),
        "{{CANONICAL_URL}}": html.escape(canonical_url("/"), quote=True),
        "{{STRUCTURED_DATA}}": dataset(len(issues), issue_page_count),
    }
    for token, value in replacements.items():
        home = home.replace(token, value)
    (OUTPUT_ROOT / "index.html").write_text(home, encoding="utf-8")

    sitemap.write(OUTPUT_ROOT / "sitemap.xml")
    (OUTPUT_ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {canonical_url('/sitemap.xml')}\n", encoding="utf-8"
    )
    site_host = urlsplit(canonical_url("/")).hostname
    if site_host and not site_host.endswith("github.io"):
        (OUTPUT_ROOT / "CNAME").write_text(f"{site_host}\n", encoding="utf-8")
    return len(all_pages)


def _breadcrumb_html(crumbs: list[Crumb]) -> str:
    items = "".join(
        f'<a href="{html.escape(crumb.path, quote=True)}">{html.escape(crumb.label)}</a>'
        if index < len(crumbs) - 1
        else f'<span aria-current="page">{html.escape(crumb.label)}</span>'
        for index, crumb in enumerate(crumbs)
    )
    return f'<span class="breadcrumb-trail">{items}</span>'


def _write_record_page(issue: GazetteIssue, page: GazettePage, text: str, sitemap: SitemapBuilder) -> None:
    printed_page = f"Printed Gazette page {page.printed_page}" if page.printed_page else "Printed page unavailable"
    source_link = "<span class=\"source-pending\">Official PDF URL not recorded</span>"
    source_detail = html.escape(issue.source_file)
    source_url = page.source.url or issue.source_url
    if source_url:
        source_href = html.escape(f"{source_url}#page={page.physical_pdf_page}", quote=True)
        source_link = f'<a class="source-link" href="{source_href}" target="_blank" rel="noopener">Open official PDF <span aria-hidden="true">↗</span></a>'
        source_detail = html.escape(str(source_url))

    record_path = f"/records/{page.uid}/"
    issue_path = f"/gazettes/{issue.issue_id}/"
    seo = record_metadata(issue.gazette_no, page.printed_page, page.physical_pdf_page, text)
    page_heading = f"Gazette No. {issue.gazette_no} - PDF page {page.physical_pdf_page}"
    crumbs = record_breadcrumbs(issue.gazette_no, issue_path, page_heading, record_path)
    structured = web_page(record_path, seo.title, seo.description, crumbs)

    template = (SOURCE_ROOT / "templates" / "page.html").read_text(encoding="utf-8")
    replacements = {
        "{{PAGE_TITLE}}": html.escape(seo.title),
        "{{PAGE_HEADING}}": html.escape(page_heading),
        "{{PAGE_DESCRIPTION}}": html.escape(seo.description),
        "{{CANONICAL_URL}}": html.escape(canonical_url(record_path), quote=True),
        "{{STRUCTURED_DATA}}": structured,
        "{{BREADCRUMBS}}": _breadcrumb_html(crumbs),
        "{{ISSUE_PATH}}": html.escape(issue_path, quote=True),
        "{{GAZETTE_NUMBER}}": html.escape(issue.gazette_no),
        "{{PUBLICATION_DATE}}": issue.publication_date.strftime("%d %B %Y"),
        "{{PHYSICAL_PAGE}}": str(page.physical_pdf_page),
        "{{PRINTED_PAGE}}": html.escape(printed_page),
        "{{SOURCE_DETAIL}}": source_detail,
        "{{SOURCE_LINK}}": source_link,
        "{{PAGE_TEXT}}": html.escape(text),
        "{{PAGE_UID}}": html.escape(page.uid),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    record_dir = OUTPUT_ROOT / "records" / page.uid
    record_dir.mkdir(parents=True, exist_ok=True)
    (record_dir / "index.html").write_text(template, encoding="utf-8")
    sitemap.add(record_path)


def _write_issue_page(
    issue: GazetteIssue, pages: list[GazettePage], texts: dict[str, str], sitemap: SitemapBuilder
) -> None:
    issue_path = f"/gazettes/{issue.issue_id}/"
    seo = issue_metadata(issue.gazette_no, issue.publication_date.strftime("%d %B %Y"), len(pages))
    crumbs = issue_breadcrumbs(issue.gazette_no, issue_path)
    structured = web_page(issue_path, seo.title, seo.description, crumbs)
    page_list = "\n".join(_sample_card(issue, page, texts[page.uid]) for page in pages)

    template = (SOURCE_ROOT / "templates" / "issue.html").read_text(encoding="utf-8")
    replacements = {
        "{{PAGE_TITLE}}": html.escape(seo.title),
        "{{PAGE_DESCRIPTION}}": html.escape(seo.description),
        "{{CANONICAL_URL}}": html.escape(canonical_url(issue_path), quote=True),
        "{{STRUCTURED_DATA}}": structured,
        "{{BREADCRUMBS}}": _breadcrumb_html(crumbs),
        "{{GAZETTE_NUMBER}}": html.escape(issue.gazette_no),
        "{{ISSUE_HEADING}}": html.escape(f"Sri Lanka Gazette No. {issue.gazette_no}"),
        "{{PUBLICATION_DATE}}": issue.publication_date.strftime("%d %B %Y"),
        "{{PAGE_COUNT}}": str(len(pages)),
        "{{PAGE_LIST}}": page_list,
        "{{ISSUE_ID}}": html.escape(issue.issue_id),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    issue_dir = OUTPUT_ROOT / "gazettes" / issue.issue_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    (issue_dir / "index.html").write_text(template, encoding="utf-8")
    sitemap.add(issue_path)


def _sample_card(issue: GazetteIssue, page: GazettePage, text: str) -> str:
    title = f"Gazette No. {issue.gazette_no} - PDF page {page.physical_pdf_page}"
    excerpt = " ".join(text.split())[:260]
    return (
        '<article class="result-card">'
        f'<a class="result-title" href="/records/{html.escape(page.uid)}/">{html.escape(title)}</a>'
        f'<p class="result-excerpt">{html.escape(excerpt)}</p>'
        "</article>"
    )


def main() -> None:
    page_count = build_site()
    print(f"Generated static site in {OUTPUT_ROOT} with {page_count} searchable pages")


if __name__ == "__main__":
    main()