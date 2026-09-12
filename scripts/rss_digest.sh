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
# reliable under cron.
export OLLAMA_HOST="http://127.0.0.1:11434"

# Virtualenv holding feedparser / ollama / requests / beautifulsoup4
VENV="$HOME/.venvs/ollama"

# Checkout location
REPO="$HOME/.gitlocal/rss_digest"

# shellcheck source=/dev/null
source "$VENV/bin/activate"

python3 "$REPO/rss_digest.py"

deactivate
