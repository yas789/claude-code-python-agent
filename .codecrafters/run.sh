#!/bin/sh
#
# This script is used to run your program on CodeCrafters
#
# This runs after .codecrafters/compile.sh
#
# Learn more: https://codecrafters.io/program-interface

set -e # Exit on failure

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

# This is done to exclude pwd from the python's path variable
# This prevents accidentally launching a module if it s present inside pwd
PYTHONSAFEPATH=1 PYTHONPATH="$PROJECT_ROOT" exec uv run \
  --project "$PROJECT_ROOT" \
  --quiet \
  -m app.main \
  "$@"
