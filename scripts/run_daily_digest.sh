#!/bin/bash
# Daily digest cron wrapper — runs at 6:00 MSK (3:00 UTC)
#
# Setup:
#   crontab -e
#   Add line: 0 3 * * * /Users/dmitriy/Documents/БескромныйAI/scripts/run_daily_digest.sh >> /Users/dmitriy/Documents/БескромныйAI/data/digest.log 2>&1

set -e

PROJECT_DIR="/Users/dmitriy/Documents/БескромныйAI"
cd "$PROJECT_DIR"

# Ensure PATH includes common python locations
export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:$PATH"

# Log header
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Daily digest run: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run the digest generator
/usr/bin/env python3 -m scripts.generate_digest

echo "Done: $(date '+%Y-%m-%d %H:%M:%S %Z')"
