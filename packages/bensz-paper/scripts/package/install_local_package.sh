#!/usr/bin/env bash
# 将 bensz-paper 安装到当前用户的本地 TeX 树（~/texmf/），
# 并安装 `bpaper` 命令行入口。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC="$PACKAGE_DIR"
DEST_BASE="${TEXMFHOME:-$HOME/texmf}"
DEST="$DEST_BASE/tex/latex/bensz-paper"
BIN_DIR="${BPAPER_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER_SRC="$DEST/bpaper"
LAUNCHER_DEST="$BIN_DIR/bpaper"
INSTALL_PYTHON_DEPS=true

DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --skip-python-deps) INSTALL_PYTHON_DEPS=false ;;
  esac
done

echo "bensz-paper — local install"
echo "  Source : $SRC"
echo "  Dest   : $DEST"
echo "  bpaper : $LAUNCHER_DEST"
[[ "$DRY_RUN" == true ]] && echo "  Mode   : dry-run (no files will be written)"
echo

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: Source directory not found: $SRC" >&2
  exit 1
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "Files that would be installed:"
  find "$SRC" -type f | while read -r f; do
    rel="${f#"$SRC/"}"
    if [[ "$rel" == *"/__pycache__/"* || "$rel" == __pycache__/* || "$rel" == *.pyc || "$rel" == .DS_Store ]]; then
      continue
    fi
    echo "  $rel"
  done
  echo
  echo "Launcher that would be linked:"
  echo "  $LAUNCHER_DEST -> $LAUNCHER_SRC"
  echo
  echo "(dry-run complete, no changes made)"
  exit 0
fi

mkdir -p "$DEST"
if [[ "$SRC" != "$DEST" ]]; then
  tar \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    -cf - -C "$SRC" . | tar -xf - -C "$DEST"
else
  echo "Source is already installed at destination; refreshing launcher and dependencies only."
fi
find "$DEST" \( -type d -name '__pycache__' -o -type f -name '*.pyc' -o -name '.DS_Store' \) -exec rm -rf {} +
chmod +x "$DEST/bml" "$DEST/bpaper" "$DEST/scripts/package/install_local_package.sh"

mkdir -p "$BIN_DIR"
ln -sf "$LAUNCHER_SRC" "$LAUNCHER_DEST"
echo "✓ Installed launcher: $LAUNCHER_DEST"

if [[ "$INSTALL_PYTHON_DEPS" == true ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required to use the bundled build tools." >&2
    exit 1
  fi
  if python3 - <<'PY'
import importlib.util
import sys

missing = [name for name in ("yaml", "docx") if importlib.util.find_spec(name) is None]
sys.exit(0 if not missing else 1)
PY
  then
    echo "Python dependencies already satisfied."
  else
    echo "Installing Python dependencies..."
    PIP_ARGS=()
    if [[ -z "${VIRTUAL_ENV:-}" && -z "${CONDA_PREFIX:-}" ]]; then
      PIP_ARGS+=(--user)
    fi
    python3 -m pip install "${PIP_ARGS[@]}" -r "$DEST/scripts/requirements.txt"
  fi
else
  echo "Skipping Python dependency installation (--skip-python-deps)"
fi

# Refresh TeX file database
if command -v mktexlsr &>/dev/null; then
  mktexlsr "$DEST_BASE" 2>/dev/null && echo "✓ mktexlsr refreshed"
else
  echo "Note: mktexlsr not found. You may need to run it manually."
fi

echo "✓ Installed to $DEST"
echo
echo "Verify with:"
echo "  kpsewhich bensz-paper.sty"
echo "  bpaper --version"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo
  echo "Note: $BIN_DIR is not currently on PATH."
  echo "Add this line to your shell profile if needed:"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi
