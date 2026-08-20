# 广东省区域联合基金青年基金报告正文模板

广东省基础与应用基础研究基金区域联合基金青年基金“报告正文”LaTeX 模板，参照 `template/广东省基础与应用基础研究基金区域联合基金青年基金项目报告正文模板.docx` 制作。项目版式以 `projects/GDNSF_General/` 为基线，单独维护区域联合青年基金的标题和提纲口径。

## 快速使用

```bash
python scripts/gdnsf_build.py build --project-dir .
```

构建脚本会使用 XeLaTeX 编译，所有中间文件进入 `.latex-cache/`，最终 PDF 保留为项目根目录下的 `main.pdf`。

## 文件结构

```text
GDNSF_General/
├── main.tex
├── extraTex/
│   ├── @config.tex
│   ├── 1.立论依据.tex
│   ├── 2.研究内容.tex
│   ├── 3.1.研究工作基础.tex
│   └── 3.2.实验条件.tex
├── figures/
└── scripts/gdnsf_build.py
```

## 说明

- 本项目是项目层独立模板，不修改 `packages/bensz-nsfc/`，避免影响 NSFC 三套模板。
- 字体优先复用已安装或仓库内的 `bensz-fonts`，并保留系统字体兜底。
- 本模板仅包含报告正文，不包含封面、申报信息表、签名页或附件清单；这些信息仍以申报系统填写为准。
- 模板保留默认关闭的水印开关；需要核对历史样稿时，可在 `extraTex/@config.tex` 中把 `\GDNSFUseSampleWatermarkfalse` 改为 `\GDNSFUseSampleWatermarktrue`。
