# 工作流：引用补齐与 DOI 可核验

适用：你希望保证“立项依据”中所有外部工作都可核验（bibkey 存在、doi 字段齐全、避免杜撰）。

路径提示：
- 在本仓库根目录运行：`python skills/nsfc-justification-writer/scripts/run.py ...`
- 在本 skill 目录运行：`python scripts/run.py ...`

## 1）生成引用核验摘要（包含缺失 bibkey / 缺 DOI 的条目）

```bash
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <你的项目>
```

## 2）手动核验与补齐 BibTeX

按上一条命令输出里的“可直接复制提示词”，逐条补充 DOI/链接/题录信息并更新 `references/*.bib`（无法核验的信息请明确标注“待核验”，不要杜撰）。

## 3）写作时的引用守护

`apply-section` 默认严格：若正文里新增 `\cite{...}` 但 `.bib` 缺 key，会拒绝写入，避免把“幻觉引用”写进标书。

如你确实要临时跳过，可使用：

```bash
python skills/nsfc-justification-writer/scripts/run.py apply-section --allow-missing-citations ...
```

不推荐长期使用：建议尽快补齐并回归严格模式。
