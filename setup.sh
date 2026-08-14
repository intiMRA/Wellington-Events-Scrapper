#!/usr/bin/env bash
#
# One-shot dev setup for Wellington-Events-Scrapper.
# Idempotent: safe to re-run. Run from the repo root:  ./setup.sh
#
set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR=".venv"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

echo "==> Checking for $PYTHON_BIN"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON_BIN not found. This project requires Python 3.11" >&2
    echo "       (StrEnum needs >=3.11; pinned TensorFlow 2.15 supports up to 3.11)." >&2
    echo "       Install it, or set PYTHON_BIN=/path/to/python3.11 and re-run." >&2
    exit 1
fi

echo "==> Creating virtual environment at $VENV_DIR (if missing)"
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "    $VENV_DIR already exists — reusing it."
fi

VENV_PY="$VENV_DIR/bin/python"

echo "==> Upgrading pip"
"$VENV_PY" -m pip install --upgrade pip

echo "==> Installing pinned dependencies (requirements.txt)"
"$VENV_PY" -m pip install -r requirements.txt

echo "==> Installing Playwright's Chromium browser"
"$VENV_PY" -m playwright install chromium

echo "==> Pre-downloading NLTK 'punkt' tokenizer (used by util/Summarizer.py)"
"$VENV_PY" - <<'PY'
import nltk
try:
    nltk.data.find("tokenizers/punkt")
    print("    punkt already present.")
except LookupError:
    nltk.download("punkt")
PY

# The Facebook scraper reads secrets from venv/.env via python-dotenv
# (see scrapers/FacebookScrapper.py). Warn if it's absent — everything else
# works without it; only the Facebook source needs it.
if [ ! -f "venv/.env" ]; then
    echo ""
    echo "NOTE: scrapers/FacebookScrapper.py expects a 'venv/.env' file with"
    echo "      Facebook credentials. It is not created by this script (secrets)."
    echo "      Create it manually if you need the Facebook source; other"
    echo "      scrapers run fine without it."
fi

echo ""
echo "==> Setup complete."
echo "    Activate with:  source $VENV_DIR/bin/activate"
echo "    Then run:       python MainScrapper.py"
