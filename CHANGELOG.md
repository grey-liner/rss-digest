# Changelog

## 1.05 — 2026-09-10

Link scraping for aggregator feeds (Hacker News, Slashdot).

- `fetch_article_text()` downloads a feed entry's link and extracts the
  readable text, stripping `script`/`style`/`nav`/`footer`/`aside` chrome and
  preferring `<article>`, `<main>`, or `[role=main]` over raw `<body>`.
- An entry whose own text is shorter than `min_content_chars` triggers a
  scrape; if the scrape returns less text than the feed already had, the feed
  text is kept.
- New config keys: `scrape_links`, `min_content_chars`, `url_timeout`,
  `max_scrape_chars`, `scrape_skip_hosts`.
- New `--no-scrape` flag, plus a per-feed `"scrape": false` override.
- Hacker News feed switched to `https://hnrss.org/frontpage`.
- `summary_prompt` rewritten. The model has no browsing ability — it only ever
  sees text this script hands it — so asking it to "visit the link" produced
  hallucinations or refusals. Fetching is now done in Python, and the prompt
  declares the body text to be scraped web content, to be treated strictly as
  data.
- `fetch_feed()` takes `cfg` rather than two loose arguments.

## 1.04 — 2026-08

- Switched model from `gemma4:e4b` to `gemma4:12b`; some articles were being
  skipped.
- Removed the prompt line instructing the model to answer
  "No summary available." for thin content — it was reaching for that far too
  readily.

## 1.02 — 2026-05

- Added the `blog.google` feed.

## 1.01

- Additional feed URLs; new output directory.

## 1.0

- Initial version: fetch feeds, summarize each entry with a local Ollama
  model, render a dated markdown digest.
