# RSS Digest Agent

Fetches RSS feeds, summarizes articles with a local Ollama LLM, and writes
a daily markdown file — ready to read when you wake up.

---

## Setup

```bash
# 1. Install dependencies
pip install feedparser ollama requests

# 2. Test it (no file saved, no LLM calls)
python rss_digest.py --dry-run --no-llm

# 3. Full run with LLM
python rss_digest.py --dry-run

# 4. Save digest to ~/Documents/digests/
python rss_digest.py
```

---

## Cron Setup (run nightly at 2 AM)

```bash
crontab -e
```

Add this line (adjust paths):

```
0 2 * * * /usr/bin/python3 /home/YOUR_USER/rss_digest/rss_digest.py >> /home/YOUR_USER/rss_digest/rss_digest.log 2>&1
```

> **Tip:** Make sure Ollama is running as a service so it's available at 2 AM:
> ```bash
> sudo systemctl enable ollama
> sudo systemctl start ollama
> ```

---

## Custom Config (optional)

Create `my_config.json` to override any setting:

```json
{
    "model": "mistral-nemo:latest",
    "output_dir": "~/Notes/digests",
    "max_articles_per_feed": 3,
    "max_age_hours": 24,
    "feeds": [
        { "name": "My Feed", "url": "https://example.com/rss" }
    ]
}
```

Then run:
```bash
python rss_digest.py --config my_config.json
```

---

## Output Format

Digests are saved as `digest_YYYY-MM-DD.md` with:
- Table of contents
- Per-feed sections
- Linked article titles
- 2–4 sentence LLM summary per article

---

## Flags

| Flag | Description |
|---|---|
| `--dry-run` | Print to stdout, don't save |
| `--no-llm` | Skip Ollama (fetch structure only) |
| `--config FILE` | Load a JSON config file |
| `--output DIR` | Override output directory |
