# GDNSF 面上项目报告正文模板

广东省自然科学基金面上项目“报告正文”LaTeX 模板，参照 `template/附件6：2025年广东省自然科学基金-面上项目申请书模板.docx` 中的报告正文提纲制作。

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
│   ├── 1.1.研究意义.tex
│   ├── 1.2.国内外研究现状.tex
│   ├── 2.1.目标内容关键问题.tex
│   ├── 2.2.研究方法技术路线.tex
│   ├── 2.3.创新之处.tex
│   ├── 2.4.年度计划预期成果.tex
│   ├── 3.1.研究工作基础.tex
│   └── 3.2.实验条件.tex
├── references/reference.tex
├── figures/
└── scripts/gdnsf_build.py
```

## 说明

- 本项目是项目层独立模板，不修改 `packages/bensz-nsfc/`，避免影响 NSFC 三套模板。
- 字体优先复用已安装或仓库内的 `bensz-fonts`，并保留系统字体兜底。
- Word 原件中的“申报书样本”属于样本文档水印，正式正文默认不启用；需要核对样稿时，可在 `extraTex/@config.tex` 中把 `\GDNSFUseSampleWatermarkfalse` 改为 `\GDNSFUseSampleWatermarktrue`。
