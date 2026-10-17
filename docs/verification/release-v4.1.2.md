# v4.1.2 发布验证

日期：2026-10-17。范围为 `v4.1.1` 至本次版本提交的完整历史、当前工作区变更与 v4.1.2 发布资产。

## 纳入文件

- 移除 `skills/nsfc-humanization/` 的全部源码、文档、配置与参考资料。
- 同步 `README.md`、`skills/README.md`、三个 NSFC 项目 `AGENTS.md`、`scripts/update_readme_skill_list.py`、`Prompts.md` 与根 `CHANGELOG.md`。
- `docs/contribution.bac` 的本次维护、打包、提交与发布证据。

## 版本历史摘要

`v4.1.1..HEAD` 在提交前没有独立已提交 commit；本次版本提交汇总了 v4.1.1 之后工作区内的全部变更。对上一版本完整历史的复核记录在任务工作区 `git-commit/input/commits-v410-v411.txt`，未把更早版本内容冒充本版本变更。

## 验证结果

| 验证 | 结果 |
| --- | --- |
| v4.1.2 标准 / Overleaf ZIP | 23 个项目，共 46 个 ZIP，生成成功 |
| ZIP 内容与缓存排除 | 待打包后复核 |
| BAC 账本 | 待提交后验证 |
| Git 差异与提交 | 待提交后验证 |

## 可复现命令

```bash
python scripts/pack_release.py --tag v4.1.2
bac --root . --bac-file docs/contribution.bac verify
git diff --check
```

## 发布资产

标准包与 Overleaf 包位于 `tests/release-v4.1.2/`，该目录为本地产物，不纳入 Git；发布时使用同一目录上传到 GitHub Release `v4.1.2`。
