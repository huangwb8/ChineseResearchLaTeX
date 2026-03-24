# thesis-ucas-doctor

`thesis-ucas-doctor` 是 `bensz-thesis` 的中国科学院大学博士论文公开示例项目。

说明：

- 版式源自上游开源项目 [`LeoJhonSong/UCAS-Dissertation`](https://github.com/LeoJhonSong/UCAS-Dissertation/tree/master)，现已按本仓库的 thesis 标准重构为“包级实现 + 项目级薄封装”
- 当前正文、摘要、附录、图表与参考文献沿用源模板中的公开内容，不额外改写为其它演示主题
- 源作者已在 [PR #36 评论](https://github.com/huangwb8/ChineseResearchLaTeX/pull/36#issuecomment-4120624795) 明确表示“你们随便用随便改”，因此本项目继续按仓库根级 MIT 口径维护
- 已通过 `tests/baselines/thesis-ucas-doctor/source-baseline.pdf` 的像素级 PDF 对比验收

构建方式：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-doctor
```

像素级比对：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py compare \
  --project-dir projects/thesis-ucas-doctor \
  --baseline-pdf tests/baselines/thesis-ucas-doctor/source-baseline.pdf \
  --build-first
```

只打开项目子目录时，可执行：

```bash
python scripts/thesis_build.py
```
