#!/usr/bin/env bash
# Checks only. Does not install software, start apps or modify client settings.
set -u

project_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
  echo '[PASS] macOS arm64'
else
  echo '[FAIL] Requires macOS arm64. On Apple Silicon, use a native terminal instead of Rosetta.'
  failed=1
fi

if command -v uv >/dev/null 2>&1; then
  echo "[PASS] $(uv --version)"
else
  echo '[FAIL] uv is missing. Install uv before preparing the project environment.'
  failed=1
fi

project_python="$project_root/.venv/bin/python"
if [[ ! -x "$project_python" ]]; then
  echo '[FAIL] Project .venv is missing. Run these commands from the project directory:'
  echo '       uv python install 3.12'
  echo '       uv sync --locked'
  exit 1
fi

if ! "$project_python" -c 'from importlib.metadata import version; [version(n) for n in ("ai-hardware-studio", "cadquery", "cadquery-ocp", "mcp", "pydantic")]' >/dev/null 2>&1; then
  echo '[FAIL] Project dependencies are incomplete. Run: uv sync --locked'
  exit 1
fi

if [[ "$failed" != 0 ]]; then
  exit 1
fi

echo '[INFO] Checking project Python, architecture and required packages; Docker is not required.'
"$project_python" -m hardware_studio.cli --artifact-root "$project_root/artifacts/cad" doctor "$@"
