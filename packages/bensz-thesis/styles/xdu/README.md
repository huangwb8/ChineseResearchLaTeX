# XDUTS

[![](https://img.shields.io/ctan/v/xduts)](https://www.ctan.org/pkg/xduts) [![](https://img.shields.io/github/v/tag/note286/xduts)](https://github.com/note286/xduts/tags) [![](https://img.shields.io/github/license/note286/xduts)](https://github.com/note286/xduts/blob/main/LICENSE) [![](https://img.shields.io/github/stars/note286/xduts)](https://github.com/note286/xduts) [![](https://img.shields.io/github/discussions/note286/xduts)](https://github.com/note286/xduts/discussions) [![](https://img.shields.io/github/issues/note286/xduts)](https://github.com/note286/xduts/issues?q=is%3Aopen+is%3Aissue) [![](https://img.shields.io/github/issues-closed/note286/xduts)](https://github.com/note286/xduts/issues?q=is%3Aissue+is%3Aclosed) [![](https://img.shields.io/github/commit-activity/m/note286/xduts)](https://github.com/note286/xduts/commits/main)

XDUTS (Xidian University TeX Suite) is a LaTeX3 document class and package suite for undergraduate/postgraduate students in Xidian University, which can be compiled with XeLaTeX on Windows, macOS, GNU/Linux, Overleaf, and TeXPage. It is designed to typesetting proposal/thesis and other documents.

XDUTS currently includes:

- `xdufont.sty`, Xidian University Font package
- `xduugtp.cls`, Xidian University Undergraduate Thesis Proposal document class
- `xdupgthesis.cls`, Xidian University Postgraduate Thesis document class
- `xduugthesis.cls`, Xidian University Undergraduate Thesis document class

In the future, we plan to add the following document class, including

- `xdupgtp.cls`, Xidian University Postgraduate Thesis Proposal document class

## Preparation

### TeX Live/MacTeX

If using TeX Live/MacTeX, make sure that the latest version of TeX Live/MacTeX is installed. Then update all packages by running command below. If on Windows, it may be necessary to start a Command Prompt as an Administrator. If on macOS or GNU/Linux, it may be necessary to run the command with `sudo`.

```shell
tlmgr update --all --self
```

### MiKTeX

If using MiKTeX, update all installed packages by running command below.

```shell
miktex packages update
```

## Installation

You can install XDUTS from either CTAN or GitHub by following the instructions below. Generally speaking, CTAN updates XDUTS slowly. If you want to use the latest version of XDUTS, get XDUTS from GitHub.

### CTAN

#### TeX Live/MacTeX/MiKTeX

After completing the preparation, run command below to open the documentation.

```shell
texdoc xduts
```

#### Overleaf/TeXPage

If you have installed LaTeX distribution locally, you can get the document class/package files and the documentation according to the [description below](#github). Otherwise, you need to download [the document class/package files](https://mirrors.cloud.tencent.com/CTAN/systems/texlive/tlnet/archive/xduts.tar.xz) and [the documentation](https://mirrors.cloud.tencent.com/CTAN/systems/texlive/tlnet/archive/xduts.doc.tar.xz) from CTAN. Finally, upload the document class/package files to the project on Overleaf/TeXPage.

### GitHub

After completing the preparation, download [this repository](https://github.com/note286/xduts/archive/refs/heads/main.zip) and run the following commands in the downloaded folder to get the document class/package files and the documentation.

```shell
xetex xduts.ins
l3build doc
```

## Update

To update, simply follow the [description above](#installation), which is the same as installation.

## Usage

Be sure to read the documentation (i.e., `xduts.pdf`) from the beginning in order to use XDUTS better.

## Note

`xdulogo.pdf` should be placed in the same directory as `xduugthesis.cls`.

## License

XDUTS is subject to [the LaTeX Project Public License version 1.3c or later version](https://www.latex-project.org/lppl.txt).
