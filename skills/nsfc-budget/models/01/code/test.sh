#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p .make_latex_model/cache

xelatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/budget_justification_xelatex_1.log
xelatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/budget_justification_xelatex_2.log

echo "编译完成: $(pwd)/main.pdf"
