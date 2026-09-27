const form = document.querySelector("#search-form");
const input = document.querySelector("#search-query");
const results = document.querySelector("#search-results");
const count = document.querySelector("#result-count");
const initialResults = results.innerHTML;
let pagefind;
let latestSearch = 0;

async function runSearch(query) {
  const requestId = ++latestSearch;
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    results.innerHTML = initialResults;
    count.textContent = `${document.querySelectorAll(".result-card").length} pages in this issue`;
    return;
  }

  count.textContent = "Searching...";
  if (!pagefind) {
    pagefind = await import("/pagefind/pagefind.js");
  }

  const response = await pagefind.search(trimmedQuery);
  const matches = await Promise.all(response.results.map((result) => result.data()));
  if (requestId !== latestSearch) return;

  results.replaceChildren(...matches.map(renderResult));
  count.textContent = `${matches.length} ${matches.length === 1 ? "page" : "pages"} found`;
  if (matches.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No matching pages in this issue.";
    results.append(empty);
  }
}

function renderResult(result) {
  const card = document.createElement("article");
  card.className = "result-card";

  const link = document.createElement("a");
  link.className = "result-title";
  link.href = result.url;
  link.textContent = result.meta?.title?.replace(" | GazetteRegistry", "") || "Gazette page";

  const excerpt = document.createElement("p");
  excerpt.className = "result-excerpt";
  excerpt.innerHTML = result.excerpt;

  card.append(link, excerpt);
  return card;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch(input.value).catch(() => {
    count.textContent = "Search index could not be loaded.";
  });
});

input.addEventListener("input", () => {
  window.clearTimeout(input.searchTimer);
  input.searchTimer = window.setTimeout(() => {
    runSearch(input.value).catch(() => {
      count.textContent = "Search index could not be loaded.";
    });
  }, 160);
});