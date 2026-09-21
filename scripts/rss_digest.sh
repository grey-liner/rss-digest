#!/bin/bash
#
# Cron wrapper for rss_digest.py.
#
# Cron runs with a minimal environment: no shell profile, no PATH you
# recognize, and no OLLAMA_HOST. Everything the script needs has to be set
# here explicitly.
#
# Install:
#   cp scripts/rss_digest.sh ~/.local/bin/rss_digest.sh
#   chmod +x ~/.local/bin/rss_digest.sh
#   crontab -e     # 30 3 * * * /home/YOU/.local/bin/rss_digest.sh
#

# Ollama server. Use an IP rather than a hostname if your resolver is not
# reliable under cron. ollama.Client() silently falls back to
# http://127.0.0.1:11434 when this is unset, so a cron run can quietly land
# on the wrong machine.
export OLLAMA_HOST="http://192.168.1.10:11434"

# Virtualenv holding feedparser / ollama / requests / beautifulsoup4
VENV="$HOME/.venvs/ollama"

# Checkout location
REPO="$HOME/.gitlocal/rss_digest"

# shellcheck source=/dev/null
source "$VENV/bin/activate"

# config.json is gitignored. Keep anything specific to your machines in it —
# ollama_host_names, output_dir, a private feed list — so the checkout stays
# publishable. It is merged over DEFAULT_CONFIG one key at a time, so a file
# naming only ollama_host_names leaves every other default alone.
# Drop the --config argument if you have no such file.
python3 "$REPO/rss_digest.py" --config "$REPO/config.json"

deactivate
