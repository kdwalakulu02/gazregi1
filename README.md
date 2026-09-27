# GazetteRegistry

The MVP indexes the Gazette PDFs in `raw/` as source-linked, searchable PDF pages. Records retain the physical PDF page and printed Gazette page; notice splitting and classification remain unassigned until they can be extracted reliably.

## Build the indexed issues

```bash
python -m pip install -r requirements.txt
for pdf in raw/*.pdf; do python scripts/extract_pdf.py "$pdf"; done
npm install
npm run build
npm run serve
```

Open <http://localhost:4173> to search the generated static site. Pagefind builds the search index locally; no database or runtime search server is used.

The PDFs do not contain their official download URLs. Supply a verified URL during extraction so the issue and page records can link to the original document:

```bash
python scripts/extract_pdf.py raw/Gazette-2026-08-14-E.pdf --source-url 'https://official.example/path/to/gazette.pdf'
npm run build
```

The example URL above is a placeholder and must be replaced with the verified government PDF URL. Repeat the command with each PDF path and its matching verified URL.

## SEO layer

Each build generates, per record and per Gazette issue: a unique `<title>`/meta description ([src/seo/metadata.py](src/seo/metadata.py)), a canonical URL ([src/seo/canonical.py](src/seo/canonical.py)), a breadcrumb trail ([src/seo/breadcrumbs.py](src/seo/breadcrumbs.py)), `WebPage`/`BreadcrumbList`/`Dataset` JSON-LD ([src/seo/structured_data.py](src/seo/structured_data.py)), and a `sitemap.xml`/`robots.txt` entry ([src/seo/sitemap.py](src/seo/sitemap.py)). Gazette issue pages (`/gazettes/<issue-id>/`) link every page in that issue; record pages link back to their issue. No search/filter query-string pages are generated or indexed.

Set `SITE_URL` before building to point canonical URLs and the sitemap at the real production domain (defaults to `https://gazetteregistry.com`):

```bash
SITE_URL=https://gazetteregistry.com npm run build
```

## Deployment

`.github/workflows/deploy.yml` builds the site on every push to `main` and deploys `dist/` to GitHub Pages via `actions/deploy-pages`. No repository secrets are required.

One-time setup:

1. In the repo, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
2. Push to `main` (or run the workflow manually) to publish the first deployment.
3. In **Settings → Pages**, set the custom domain to `gazetteregistry.com`. GitHub Pages reads the `CNAME` file the build writes into `dist/` (derived from `SITE_URL`) and will offer to enforce HTTPS once DNS is verified.
4. In Cloudflare DNS for `gazetteregistry.com`, add a `CNAME` record for the apex/`www` host pointing to `<github-username>.github.io`, proxy status **DNS only** (grey cloud) until GitHub issues the HTTPS certificate, then optionally switch to proxied.

Set `SITE_URL` in the workflow env (already `https://gazetteregistry.com`) to match the domain configured in Cloudflare/GitHub Pages.