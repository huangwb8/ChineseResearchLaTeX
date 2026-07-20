# GXNSF 面上项目报告正文模板

广西自然科学基金面上项目“报告正文”LaTeX 模板，参照 issue #52 提供的 `template/广西自然科学基金面上项目-报告正文.docx` 制作。

项目已内置一套以佐佐木希公开职业资料为贯穿案例的计算传播示例正文，用于展示十五个内容插槽、公式、表格和参考文献的实际排版效果。示例中的人员履历、项目经历、工作条件和成果指标均为明确标注的占位内容，不构成真实申请材料；使用时请按本人情况完整替换。

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
- 标题与条目采用仿宋语义字体，一级提纲采用楷体语义字体；全文 `16 pt`，固定 `28.3 pt` 行距，首行缩进两字符。标题和条目标题沿用原 DOCX 的仿宋加粗设置。
- 原 DOCX 指定“方正仿宋_GBK / 方正楷体_GBK”。本模板优先使用系统已安装的对应方正字体（兼容“方正仿宋简体 / 方正楷体简体”家族名）；否则使用 `bensz-fonts` 内置的同款方正字体；再依次回退到 `Microsoft YaHei`、Adobe 仿宋和楷体。Overleaf 包会携带所需的最小字体运行时。
- 参考来源：[issue #52](https://github.com/huangwb8/ChineseResearchLaTeX/issues/52)、[广西师范大学 2025 年度广西科技计划项目申报通知](http://www.research.gxnu.edu.cn/_t7/2024/0619/c533a291018/pagem.htm)及其附件四。

## 适用边界

本项目只复刻 issue 附件中的广西自然科学基金面上项目精简“报告正文”提纲，不包含封面、申请信息表、签章页，也不替代当年度申报须知与系统附件要求。正式申报前请以广西科技管理信息平台当年发布的要求为准。

示例研究只使用可核验的公开人物资料演示“多模态时序数据—跨媒介状态转移—职业韧性”的写作结构，不对佐佐木希的私人生活、心理状态或个人价值作推断。公开数据的采集、保存和再发布仍应遵守来源网站条款、版权与隐私要求。

本模板在项目层独立维护，不修改或依赖 `packages/bensz-nsfc/`，因此不会改变国家自然科学基金及其它省级模板的样式。
