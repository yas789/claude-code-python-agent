#!/bin/sh
#
# Use this script to run your program LOCALLY.
#
# Note: Changing this script WILL NOT affect how CodeCrafters runs your program.
#
# Learn more: https://codecrafters.io/program-interface

set -e # Exit early if any commands fail

# Default local runs to Ollama. Explicit environment values take precedence.
export OPENROUTER_BASE_URL="${OPENROUTER_BASE_URL:-http://localhost:11434/v1}"
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-ollama}"

# Copied from .codecrafters/run.sh
#
# - Edit this to change how your program runs locally
# - Edit .codecrafters/run.sh to change how your program runs remotely
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHONSAFEPATH=1 PYTHONPATH="$PROJECT_ROOT" exec uv run \
  --project "$PROJECT_ROOT" \
  --quiet \
  -m app.main \
  --model granite3.3:2b \
  "$@"
