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

DOCX 导出（UCAS 资环 Word 对齐链路）：

```bash
python3 projects/thesis-ucas-doctor/scripts/export_docx.py \
  --project-dir projects/thesis-ucas-doctor
```

如果模板文件不在项目根目录，再显式指定：

```bash
python3 projects/thesis-ucas-doctor/scripts/export_docx.py \
  --project-dir projects/thesis-ucas-doctor \
  --reference-doc <path-to-reference.docx>
```

该脚本会生成：

- `main_from_tex_word_source.md`：源码转 Word 的中间稿
- `main_from_tex_资环模板.docx`：按参考模板套样式后的 Word 初稿
- `main_from_tex_资环模板_质量报告.md`：针对资环分委会版式要求的自动检查报告

说明：

- 脚本默认会优先寻找 `docs/official/` 下由用户自行放置的官方 Word 模板（其次兼容项目根目录与 `docs/`）
- 该链路优先对齐正文、摘要、标题层级与版面参数
- 图表、算法和代码环境仍会按“人工整理”思路降级处理
- 当前 DOCX 导出为 `thesis-ucas-doctor` 项目级对齐能力，仅用于资环模板结构与版式参考；该链路尚不完善，不构成 `bensz-thesis` 通用 DOCX 支持，复杂对象（图表/算法/代码环境/交叉引用等）仍需人工复核与整理，后续将持续优化

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
python3 projects/thesis-ucas-doctor/scripts/export_docx.py --project-dir projects/thesis-ucas-doctor
```

`main_from_tex_资环模板_质量报告.md` 中以下项应为 PASS：

- 纸张A4(210x297mm, 表3)
- 页边距与页眉页脚距离(表3)
- 正文样式字体(宋体+Times New Roman, 表7)
- 正文样式行距/首行缩进(1.25倍/两字符, 表7)
- 正文是否超过三级标题(0083)
- 章节存在：摘要 / Abstract / 目录 / 图表目录 / 参考文献 / 致谢

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
