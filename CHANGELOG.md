# Changelog

## 1.08 — 2026-09-12

Stop paying for reasoning this script throws away.

`gemma4:31b` is a thinking model: it emits a hidden reasoning trace into
`message["thinking"]` before its answer, and `summarize()` reads only
`message["content"]`. Every one of those tokens was generated at full cost and
discarded. Measured over three real Hacker News articles on a remote LAN box:

| | per article |
|---|---|
| thinking on, 32k context (previous behaviour) | 76.7s |
| thinking off, `num_ctx` 8192 | 17.9s |
| thinking off, `num_ctx` 4096 | **13.1s** |

- New `think` config key, default `False`, with `--think` to restore the old
  behaviour for comparison.
- New `num_ctx` config key, default `4096`, with `--num-ctx N` to override and
  `0` to defer to the model. Prompts here measured 1272 tokens at worst across
  these feeds, bounded by `max_content_chars`, so 4096 leaves ~2x headroom.
- `summarize()` now reports an empty `content` field rather than returning an
  empty string. A thinking model that runs out of room answers entirely in
  `thinking` and leaves `content` blank, which silently produced empty entries
  and is the likely cause of the "some summaries appear to be skipped" note in
  1.04.
- Both settings appear in the log banner and the digest header.

## 1.07 — 2026-09-11

Report which Ollama server did the work.

Two servers on one LAN are easy to confuse, and `ollama.Client()` falls back to
`http://127.0.0.1:11434` without complaint when `OLLAMA_HOST` is unset — so a
run can quietly land on the wrong machine and simply take hours longer, with
nothing in the output to say so.

- The digest header now names the resolved endpoint, whether it is this machine
  or a remote one, and the server version.
- Model residency is read from `/api/ps` after the first summarization: how
  much of the model is in VRAM, and how much spilled to system RAM. This is
  usually the real answer to "why was it slow".
- A run that resolves to a local address is flagged in both the digest and the
  log, stating whether `OLLAMA_HOST` was set.
- Elapsed time and seconds-per-article are recorded in the header and footer.
- New `ollama_host_names` config key maps a host or IP to a friendly name, since
  LAN boxes rarely have reverse DNS.
- `summarize()` takes an explicit `ollama.Client`, so the URL reported is
  provably the one the requests went to.

## 1.06 — 2026-09-11

- `article_age_hours()` used `time.mktime()` on feedparser's `*_parsed`
  timestamp. Those are normalized to UTC, and `mktime()` interprets its
  argument as local time, so every article's age was off by the machine's UTC
  offset — entries near the `max_age_hours` boundary were included or dropped
  incorrectly. Now uses `calendar.timegm()`.
- The trailing "End Processing at DateTime" line was missing its closing `*`,
  so it rendered as literal text rather than emphasis.

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
