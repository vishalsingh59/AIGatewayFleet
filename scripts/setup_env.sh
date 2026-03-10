#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MISSING=0

ok() { echo "[OK]   $1"; }
fail() { echo "[MISS] $1"; MISSING=1; }

check_cmd() {
  local cmd="$1"
  local label="$2"
  if command -v "${cmd}" >/dev/null 2>&1; then
    ok "${label}"
  else
    fail "${label}"
  fi
}

check_python_version() {
  if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 (>= 3.8)"
    return
  fi

  local py_out
  py_out="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

  local major minor
  major="${py_out%%.*}"
  minor="${py_out##*.}"

  if [[ "${major}" -gt 3 || ( "${major}" -eq 3 && "${minor}" -ge 8 ) ]]; then
    ok "python3 >= 3.8 (found ${py_out})"
  else
    fail "python3 >= 3.8 (found ${py_out})"
  fi
}

echo "--------------------------------------"
echo "Checking local runtime prerequisites"
echo "--------------------------------------"
check_python_version
check_cmd "openssl" "openssl"
check_cmd "curl" "curl"

if python3 -m venv --help >/dev/null 2>&1; then
  ok "python3 venv module"
else
  fail "python3 venv module"
fi

if [[ "${MISSING}" -eq 1 ]]; then
  echo ""
  echo "Missing prerequisites detected. Install missing tools and rerun ./scripts/setup_env.sh."
  exit 1
fi

echo "--------------------------------------"
echo "Setting up Python development environment"
echo "--------------------------------------"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
python3 -m pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

echo ""
echo "--------------------------------------"
echo "Environment setup complete"
echo "--------------------------------------"
echo ""
echo "Activate environment with:"
echo "source venv/bin/activate"
