#!/usr/bin/env bash
# Build and optionally upload memnet-llm to PyPI.
# Prerequisites: pip install hatch twine
# Auth (upload only): TWINE_USERNAME=__token__ (default); TWINE_PASSWORD already set
# Never print or write the token.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UPLOAD=0
for arg in "$@"; do
  case "$arg" in
    --upload) UPLOAD=1 ;;
    -h|--help)
      echo "Usage: ./scripts/publish.sh [--upload]"
      echo "  Builds sdist+wheel and runs twine check."
      echo "  Uploads only with --upload when TWINE_PASSWORD is already set."
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: ./scripts/publish.sh [--upload]" >&2
      exit 2
      ;;
  esac
done

echo "Building sdist + wheel..."
python -m hatch build

echo "Checking dist..."
python -m twine check dist/*

if [[ "$UPLOAD" -eq 1 ]]; then
  if [[ -z "${TWINE_PASSWORD:-}" ]]; then
    echo "Refusing upload: TWINE_PASSWORD is not set in the environment." >&2
    echo "Set TWINE_USERNAME=__token__ (optional; defaulted) and TWINE_PASSWORD, then re-run with --upload." >&2
    exit 1
  fi
  export TWINE_USERNAME="${TWINE_USERNAME:-__token__}"
  echo "Uploading to PyPI..."
  python -m twine upload dist/*
else
  if [[ -z "${TWINE_PASSWORD:-}" ]]; then
    echo ""
    echo "Build OK. To upload: set TWINE_USERNAME=__token__ and TWINE_PASSWORD, then:"
    echo "  ./scripts/publish.sh --upload"
  else
    echo "Build OK. Run: ./scripts/publish.sh --upload"
  fi
fi
