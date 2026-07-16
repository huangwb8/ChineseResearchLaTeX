# GXNSF 面上项目报告正文模板

广西自然科学基金面上项目“报告正文”LaTeX 模板，参照 issue #52 提供的 `template/广西自然科学基金面上项目-报告正文.docx` 制作。

## 快速使用

```bash
python scripts/gxnsf_build.py build --project-dir .
```

构建脚本使用 XeLaTeX 编译两轮，所有中间文件进入 `.latex-cache/`，最终 PDF 保留为项目根目录下的 `main.pdf`。推荐直接用 `GXNSF_General.code-workspace` 打开 VS Code。

标准 zip 使用前需要安装共享字体包。在完整仓库根目录执行：

```bash
python3 scripts/install.py install --packages bensz-fonts
```

只下载了单项目 zip 时，可使用根级安装器的远程入口：

```bash
curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py | python3 - install --packages bensz-fonts
```

Overleaf zip 已内嵌最小字体运行时，无需执行上述安装。

## 文件结构

```text
GXNSF_General/
├── main.tex
├── extraTex/
│   ├── @config.tex
│   ├── 1.1.立项依据.tex
│   ├── ...
│   └── 4.其他附件清单.tex
├── figures/
├── template/
└── scripts/gxnsf_build.py
```

## 版式与来源

- A4 页面；上下边距 `2.54 cm`，左右边距 `3.175 cm`。
- 标题与条目采用仿宋语义字体，一级提纲采用楷体语义字体；全文 `16 pt`，固定 `28.3 pt` 行距，首行缩进两字符。
- 标准包统一复用 `bensz-fonts` 中的 Adobe 仿宋、楷体和 Times New Roman 兼容字体，避免不同操作系统的字体名称差异；Overleaf 包会携带同一组最小字体运行时。
- 参考来源：[issue #52](https://github.com/huangwb8/ChineseResearchLaTeX/issues/52)、[广西师范大学 2025 年度广西科技计划项目申报通知](http://www.research.gxnu.edu.cn/_t7/2024/0619/c533a291018/pagem.htm)及其附件四。

## 适用边界

本项目只复刻 issue 附件中的广西自然科学基金面上项目精简“报告正文”提纲，不包含封面、申请信息表、签章页，也不替代当年度申报须知与系统附件要求。正式申报前请以广西科技管理信息平台当年发布的要求为准。

本模板在项目层独立维护，不修改或依赖 `packages/bensz-nsfc/`，因此不会改变国家自然科学基金及其它省级模板的样式。
