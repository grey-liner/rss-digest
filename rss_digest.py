#!/usr/bin/env python3
"""
rss_digest.py — Autonomous RSS Digest Agent
Fetches RSS feeds, summarizes articles via Ollama, and writes a
daily markdown digest. Designed to run unattended via cron.

Usage:
    python rss_digest.py               # Run with defaults
    python rss_digest.py --dry-run     # Print output, don't save
    python rss_digest.py --config my_feeds.json

Requirements:
    pip install feedparser ollama requests
    
    
Version 1.0
    1.0   Original by Claude
    1.01  Updated with additional site urls and new output directory
    1.02  Added google.blog.feed
    1.04  Some summaries appear to be skipped
        Changed model to gemma4:12b to try to overcome gemma4:e4b 
        Removed prompt line: "If the content is too thin to summarize, say 'No summary available.'
        
"""

import argparse
import json
import logging
# import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import feedparser
import ollama

# ─────────────────────────────────────────────
#  CONFIGURATION  (edit freely)
# ─────────────────────────────────────────────

DEFAULT_CONFIG = {
    # Ollama model to use for summarization
    #"model": "mistral-nemo:latest",
    #"model": "gemma4:e4b",
    "model":"gemma4:12B",

    # Where to write digest files (~ is expanded automatically)
    #"output_dir": "~/Documents/digests",
    "output_dir": "~/dropbox/output/digests",

    # Max articles to pull per feed (keep low to control runtime)
    "max_articles_per_feed": 100,

    # Max characters of article description/content sent to the LLM
    # Longer = richer summaries, but slower.  ~2000 is a good balance.
    "max_content_chars": 2500,

    # Seconds to wait between Ollama calls (be kind to your GPU)
    "request_delay": 5.0,

    # Only include articles published within this many hours
    # Set to 0 to disable date filtering
    "max_age_hours": 48,

    # Summarization style prompt (feel free to tune this)
    #"summary_prompt": (
    #    "You are a concise technical news summarizer. "
    #    "Given the title and content of an article, write a 2-5 sentence "
    #    "plain-English summary. Focus on what is new or notable. "
    #    "Do not editorialize or add opinions. "
    #    "If the content is too thin to summarize, say 'No summary available.'"
    #)
    "summary_prompt": (
        "You are a technical news summarizer. "
        "Visit the link to each article and review the content of that article."
        "Given the title and content of an article, write a concise 2-5 sentence "
        "plain-English summary. Focus on what is new or notable. "             
    ),

    # Additional Feeds: though this one is weekly so 168 hours
    # since it's a weekly newsletter rather than daily, you may want to bump your max_age_hours to 168 (7 days) in your config so the age filter doesn't exclude its posts. 
    # {
    #     "name": "Last Week in AI",
    #     "url": "https://lastweekin.ai/feed"
    # },



    # RSS feeds to monitor
    "feeds": [
        # ── AI / LLM ──────────────────────────────────────────────
        {
            "name": "Hugging Face Blog",
            "url": "https://huggingface.co/blog/feed.xml"
        },
        {
            "name": "The Batch (deeplearning.ai)",
            "url": "https://www.deeplearning.ai/the-batch/feed/"
        },
        {
            "name": "Andrej Karpathy (Substack)",
            "url": "https://karpathy.substack.com/feed"
        },
        # ── Linux / Open Source ───────────────────────────────────
        {
            "name": "Phoronix",
            "url": "https://www.phoronix.com/rss.php"
        },
        {
            "name": "OMG! Ubuntu",
            "url": "https://www.omgubuntu.co.uk/feed"
        },
        # ── Science Fiction ───────────────────────────────────────
        {
            "name": "Tor.com",
            "url": "https://www.tor.com/feed/"
        },
        # ── General Tech ──────────────────────────────────────────
        {
            "name": "Ars Technica - Technology",
            "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"
				
		},		
		# -- Individual Picks ---
		{
 			"name": "Last Week in AI",
  			"url": "https://lastweekin.ai/feed"
		},
        {
            "name": "Slashdot",
            "url": "https://rss.slashdot.org/Slashdot/slashdotMain" 
        },
        {
             "name": "Latent Space",
             "url": "https://www.latent.space/feed"         
        },        
        {
            "name": "Ahead of AI",
            "url": "https://magazine.sebastianraschka.com/feed"
        },   
        {
           "name":"Google Blog",
           "url":"https://blog.google/feed/"
        },
        {
           "name":"Harper Reeds Blog",
           "url":"https://harper.blog/index.xml"
        },
        
        {
        	"name":"Hacker News",
        	"url":"https://news.ycombinator.com/rss"
        },
        
		# -- Random Crap
		{
			"name": "Hwat! - podcast",
			"url": "https://rss.art19.com/hwat-weekly"
        },
    ]
}

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rss_digest")


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def load_config(path: str | None) -> dict:
    """Merge a JSON config file over the defaults."""
    cfg = DEFAULT_CONFIG.copy()
    if path:
        with open(path) as f:
            overrides = json.load(f)
        cfg.update(overrides)
    return cfg


def strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def article_age_hours(entry) -> float:
    """Return how many hours ago an entry was published. 0 if unknown."""
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return 0.0
    pub_ts = time.mktime(published)
    return (time.time() - pub_ts) / 3600


def fetch_feed(feed_cfg: dict, max_articles: int, max_age_hours: float) -> list[dict]:
    """Download and parse one RSS feed. Returns a list of article dicts."""
    url = feed_cfg["url"]
    log.info(f"  Fetching: {feed_cfg['name']}  ({url})")
    try:
        parsed = feedparser.parse(url, agent="rss_digest/1.0")
    except Exception as e:
        log.warning(f"  ✗ Failed to fetch {url}: {e}")
        return []

    if parsed.bozo and not parsed.entries:
        log.warning(f"  ✗ Malformed feed: {url}")
        return []

    articles = []
    for entry in parsed.entries[:max_articles]:
        # Age filter
        if max_age_hours > 0:
            age = article_age_hours(entry)
            if age > max_age_hours:
                log.debug(f"    Skipping old article ({age:.0f}h): {entry.get('title','?')}")
                continue

        # Build content blob from whatever fields exist
        title   = strip_html(entry.get("title", "Untitled"))
        summary = strip_html(entry.get("summary", ""))
        content_list = entry.get("content", [])
        body = strip_html(content_list[0].get("value", "")) if content_list else ""
        content = body or summary

        articles.append({
            "title":   title,
            "url":     entry.get("link", ""),
            "content": content,
            "published": entry.get("published", ""),
        })

    log.info(f"    → {len(articles)} article(s) within age limit")
    return articles


def summarize(article: dict, cfg: dict) -> str:
    """Call Ollama to summarize one article. Returns summary string."""
    title   = article["title"]
    content = article["content"][:cfg["max_content_chars"]]

    user_msg = f"Title: {title}\n\nContent:\n{content}"

    try:
        response = ollama.chat(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": cfg["summary_prompt"]},
                {"role": "user",   "content": user_msg},
            ],
        )
        return response["message"]["content"].strip()
    except Exception as e:
        log.warning(f"    ✗ Ollama error for '{title}': {e}")
        return "_Summary unavailable (LLM error)._"


# ─────────────────────────────────────────────
#  MARKDOWN RENDERER
# ─────────────────────────────────────────────

def render_markdown(sections: list[dict], cfg: dict) -> str:
    """Build the full markdown digest document."""
    date_str = datetime.now().strftime("%A, %B %-d, %Y")
    time_str = datetime.now().strftime("%I:%M %p")
    model    = cfg["model"]

    lines = [
        f"# 📰 Daily Digest — {date_str}",
        f"",
        f"> Generated at {time_str} by `rss_digest.py` using `{model}`.",
        f"",
        "---",
        "",
    ]

    if not sections:
        lines.append("_No new articles found within the configured time window._")
        return "\n".join(lines)

    # Table of contents
    lines.append("## Table of Contents")
    lines.append("")
    for sec in sections:
        anchor = re.sub(r"[^a-z0-9]+", "-", sec["feed"].lower()).strip("-")
        count  = len(sec["articles"])
        lines.append(f"- [{sec['feed']}](#{anchor}) — {count} article{'s' if count != 1 else ''}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Feed sections
    for sec in sections:
        lines.append(f"## {sec['feed']}")
        lines.append("")

        for art in sec["articles"]:
            title   = art["title"]
            url     = art["url"]
            pub     = art.get("published", "")
            summary = art["summary"]

            lines.append(f"### [{title}]({url})")
            if pub:
                lines.append(f"*{pub}*")
                lines.append("")
            lines.append(summary)
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append(f"*End of digest. {sum(len(s['articles']) for s in sections)} articles summarized.*")
    
    date_str = datetime.now().strftime("%A, %B %-d, %Y")
    time_str = datetime.now().strftime("%I:%M %p")
    lines.append(f"*End Processing at DateTime: {date_str} {time_str}")
    
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Autonomous RSS Digest Agent")
    parser.add_argument("--config",   help="Path to JSON config file")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print digest to stdout instead of saving")
    parser.add_argument("--no-llm",   action="store_true",
                        help="Skip LLM summarization (fetch + structure only)")
    parser.add_argument("--output",   help="Override output directory")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output:
        cfg["output_dir"] = args.output

    output_dir = Path(cfg["output_dir"]).expanduser()

    log.info("=" * 55)
    log.info("  RSS Digest Agent starting")
    log.info(f"  Model   : {cfg['model']}")
    log.info(f"  Feeds   : {len(cfg['feeds'])}")
    log.info(f"  Max age : {cfg['max_age_hours']}h")
    log.info(f"  Output  : {output_dir}")
    log.info("=" * 55)

    sections = []

    for feed_cfg in cfg["feeds"]:
        articles = fetch_feed(
            feed_cfg,
            cfg["max_articles_per_feed"],
            cfg["max_age_hours"],
        )

        if not articles:
            continue

        summarized = []
        for art in articles:
            if args.no_llm:
                art["summary"] = strip_html(art["content"])[:300] + "…"
            else:
                log.info(f"    Summarizing: {art['title'][:60]}…")
                art["summary"] = summarize(art, cfg)
                time.sleep(cfg["request_delay"])
            summarized.append(art)

        if summarized:
            sections.append({
                "feed":     feed_cfg["name"],
                "articles": summarized,
            })

    # Render
    digest = render_markdown(sections, cfg)

    if args.dry_run:
        print(digest)
        sys.exit(0)

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("digest_%Y-%m-%d.md")
    out_path = output_dir / filename

    out_path.write_text(digest, encoding="utf-8")

    total = sum(len(s["articles"]) for s in sections)
    log.info("=" * 55)
    log.info(f"  ✓ Digest saved: {out_path}")
    log.info(f"  ✓ {total} articles across {len(sections)} feeds")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
