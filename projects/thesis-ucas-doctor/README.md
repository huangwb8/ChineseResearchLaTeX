# thesis-ucas-doctor

`thesis-ucas-doctor` 是 `bensz-thesis` 的中国科学院大学博士论文公开示例项目。

说明：

- 版式源自上游开源项目 [`LeoJhonSong/UCAS-Dissertation`](https://github.com/LeoJhonSong/UCAS-Dissertation/tree/master)，现已按本仓库的 thesis 标准重构为“包级实现 + 项目级薄封装”
- 当前正文、摘要、附录、图表与参考文献沿用源模板中的公开内容，不额外改写为其它演示主题
- 源作者已在 [PR #36 评论](https://github.com/huangwb8/ChineseResearchLaTeX/pull/36#issuecomment-4120624795) 明确表示“你们随便用随便改”，因此本项目继续按仓库根级 MIT 口径维护
- 当前仓库默认不附带公开的像素级基线 PDF；如需做版式回归，请使用你自己的基线文件运行 `compare`

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor
```

书脊独立构建（不并入主论文 PDF）：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build \
  --project-dir projects/thesis-ucas-doctor \
  --tex-file spine.tex
```

DOCX 初稿导出：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx \
  --project-dir projects/thesis-ucas-doctor
```

如需套用学校 Word 模板，显式指定 `--reference-doc`：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx \
  --project-dir projects/thesis-ucas-doctor \
  --reference-doc <path-to-reference.docx>
```

该命令会生成：

- `main.docx`：从 LaTeX 源生成的可编辑 Word draft
- `.latex-cache/docx/main.md`：源码转 Word 的中间 Markdown
- `.latex-cache/docx/main_docx_quality_report.md`：导出质量报告，包含缺失资源、降级对象、样式映射与人工复核提示

说明：

- `bensz-thesis` 通用 DOCX 导出会按 `--reference-doc`、`artifacts/reference.docx`、`docs/official/*.docx`、`docs/*.docx` 的顺序发现参考 Word 模板；未找到时会使用 Pandoc 默认样式，并在质量报告中提示
- 该链路定位为“可编辑 Word 初稿”，优先保留标题、正文、列表、图片、基础公式与基础引用，不承诺与 PDF 像素级一致
- 图表、算法、代码环境、TikZ 与复杂宏仍会按“人工整理”思路降级处理，并把原始 LaTeX 保存到 `.latex-cache/docx/unsupported/`
- `scripts/export_docx.py` 仍作为兼容旧命令的薄 wrapper 保留一个发布周期；新用法建议直接调用 `thesis_project_tool.py docx`

官方参考资料（元数据与校验目录）：

- `docs/official/SHA256SUMS.txt`
- `docs/official/README.md`

说明：

- 仓库不直接分发 UCAS 官方 `.doc/.docx` 原件；请按 [`docs/official/README.md`](docs/official/README.md) 中的来源页面自行下载，并放入 `docs/official/`
- `export_docx.py` 只依赖 Word 模板 `.docx`；“撰写具体要” `.doc` 仅用于人工核对条款与验收口径
- 下载后可用 `sha256sum -c docs/official/SHA256SUMS.txt` 校验完整性

资环一致性验收：

- 对照基线文档：[`docs/ucas_resource_env_alignment_matrix.md`](docs/ucas_resource_env_alignment_matrix.md)
- 本项目采用“结构与版式优先”验收口径：先对齐资环模板结构和版面，再处理内容型指标（如摘要最终字数）
- 目录域是否已在 Word 内更新保留提示，不作为失败项

建议按以下顺序执行：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor --tex-file spine.tex
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-ucas-doctor
```

像素级比对（需自备基线 PDF）：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py compare \
  --project-dir projects/thesis-ucas-doctor \
  --baseline-pdf <path-to-baseline.pdf> \
  --build-first
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
