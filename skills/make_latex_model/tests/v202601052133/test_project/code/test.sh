#!/bin/bash
echo "NSFC LaTeX 项目编译脚本"
xelatex -interaction=nonstopmode main.tex
bibtex main
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex

