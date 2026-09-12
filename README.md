# RSS Digest Agent

Fetches a list of RSS feeds, summarizes each article with a local
[Ollama](https://ollama.com) model, and writes a dated markdown digest — ready
to read when you wake up.

Nothing leaves the machine. The only outbound traffic is the feed fetches and,
for aggregator feeds, the article pages themselves.

```
📰 Daily Digest — Friday, September 11, 2026

> Generated at 03:31 AM by `rss_digest.py` using `gemma4:31b`.

## Hacker News
### [Some article title](https://example.com/post)
*Fri, 11 Sep 2026 02:14:00 +0000* · `🔗 full article scraped`
Two to six sentences on what is actually new here…
```

---

## Setup

```bash
python3 -m venv ~/.venvs/ollama
source ~/.venvs/ollama/bin/activate
pip install -r requirements.txt

# Structure only — no model calls, nothing written
python3 rss_digest.py --dry-run --no-llm

# Full run, printed to stdout
python3 rss_digest.py --dry-run

# For real
python3 rss_digest.py
```

The model named in the config must already be pulled (`ollama pull <model>`),
and the Ollama server must be reachable. If it runs on another box, set
`OLLAMA_HOST`:

```bash
export OLLAMA_HOST="http://192.168.1.10:11434"
```

---

## Flags

| Flag | Description |
|---|---|
| `--dry-run` | Print to stdout instead of saving |
| `--no-llm` | Skip Ollama; truncate the source text instead of summarizing |
| `--no-scrape` | Never follow article links, even for thin entries |
| `--config FILE` | Load a JSON config file over the defaults |
| `--output DIR` | Override the output directory |

---

## Configuration

Defaults live in `DEFAULT_CONFIG` at the top of `rss_digest.py`. A JSON file
passed with `--config` is merged over them, key by key — so a config naming
only `model` and `feeds` leaves every other default intact.

`config.example.json` is a dump of the current defaults; copy it to
`config.json` (gitignored) and edit.

| Key | Default | Notes |
|---|---|---|
| `model` | `gemma4:31b` | Any pulled Ollama model |
| `output_dir` | `~/dropbox/output/digests` | `~` is expanded |
| `max_articles_per_feed` | `100` | Applied before the age filter |
| `max_content_chars` | `2500` | How much text reaches the model |
| `request_delay` | `10.0` | Seconds between Ollama calls |
| `max_age_hours` | `48` | `0` disables the age filter |
| `scrape_links` | `true` | Master switch for link scraping |
| `min_content_chars` | `400` | Feed text below this triggers a scrape |
| `url_timeout` | `12` | Seconds before abandoning a page |
| `max_scrape_chars` | `20000` | Hard cap before trimming to `max_content_chars` |
| `scrape_skip_hosts` | see config | Paywalls, JS-only apps, media hosts |
| `summary_prompt` | see config | System prompt |
| `feeds` | see config | `[{ "name": ..., "url": ..., "scrape": false }]` |

A weekly feed needs `max_age_hours` raised to `168`, or its posts fall outside
the window on six days out of seven.

---

## Link scraping

Aggregator feeds are the reason this exists. A Hacker News `<description>` is
about 150 characters of points-and-comments metadata; the article itself lives
at `<link>`. Summarizing the description alone produces nothing worth reading.

When an entry's own text is shorter than `min_content_chars`, the script
fetches the linked page, strips `script`, `style`, `nav`, `footer`, `header`,
`aside`, `form`, and friends, and prefers `<article>`, `<main>`, or
`[role=main]` over the raw `<body>`. If the scrape comes back with less text
than the feed already had, the feed text is kept. Scraped articles are marked
`🔗 full article scraped` in the digest.

Hosts in `scrape_skip_hosts` and URLs pointing at media files are never
fetched. Per-feed, `"scrape": false` opts a single feed out.

**The model does not browse.** It only ever sees text this script hands it.
An earlier version asked the model in its system prompt to open the link and
read the article; it cannot, and it responded with hallucinated summaries or
refusals. The fetching moved to Python in 1.05, and the prompt now declares the
body text to be scraped web content, to be treated strictly as data rather than
as instructions.

---

## Running from cron

`scripts/rss_digest.sh` is the wrapper. Cron gives you almost no environment —
no shell profile, no `OLLAMA_HOST`, and a `PATH` you would not recognize — so
the wrapper sets the Ollama host, activates the virtualenv, and calls the
script by absolute path.

```bash
cp scripts/rss_digest.sh ~/.local/bin/rss_digest.sh
chmod +x ~/.local/bin/rss_digest.sh
crontab -e
```

```
30 3 * * * /home/YOUR_USER/.local/bin/rss_digest.sh
```

Make sure Ollama survives a reboot:

```bash
sudo systemctl enable --now ollama
```

Runtime is dominated by `request_delay` times the article count, so a wide feed
list at 10 seconds a call takes a while. That is the point of running it at
3:30 AM.

---

## Output

`digest_YYYY-MM-DD.md`, containing a table of contents, one section per feed,
linked article titles with publication dates, and a summary per article.

---

## Origins

Written with Claude and revised in place over several months; see
[CHANGELOG.md](CHANGELOG.md). The commits before 2026-09-11 were reconstructed
from saved copies on disk, dated by file mtime.
