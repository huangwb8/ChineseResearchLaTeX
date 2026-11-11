# v4.1.3 发布验证

日期：2026-11-12。历史范围为 `v4.1.2..v4.1.3`，包含发布任务开始前的 19 个提交、本次四川大学示例提交及最终版本提交。

## 版本范围

本版新增四川大学硕士论文模板，恢复综述质量与正式交付布局，整理文献检索契约及依赖，并更新 NSFC 立项依据、研究内容写作与安全修订流程。版本提交和 Release Notes 依据整个版本区间归纳；兼容性变化见根 CHANGELOG 的 4.1.3 章节。

本次保存四川大学示例的 README、元数据、双语摘要、正文、书目、附录与 PDF；发布提交同步 Prompts、README 下载链接和 Skill 清单、CHANGELOG、本验证记录及贡献账本。README 模板清单缺失的结束标记已补回，恢复自动同步入口。

## 验证结果

| 验证 | 结果 |
| --- | --- |
| 标准版 / Overleaf ZIP | 24 个项目，共 48 个 ZIP，生成成功 |
| ZIP 完整性 | 全量 CRC、归档路径、缓存排除通过；四川大学元数据与源码一致 |
| 四川大学独立项目 | 2 项通过，包含隔离环境下官方 wrapper 编译、纸型、版心与连续脚注 |
| 综述质量与本地缺陷回归 | 47 项通过 |
| 立项依据修订安全检查 | 正式 CLI 入口运行，12 项通过 |
| 研究内容修订安全回归 | 正式 CLI 入口运行，29 项通过，无错误或失败 |
| BAC 初验 | 哈希链检查未报错误；保留 3 条既有 actor/source_type 类型警告，签名状态 unsigned |
| Git 差异 | `git diff --check` 通过；提交默认运行本地 Git hooks |

首次误用 pytest 汇总两个 NSFC 脚本，先遇到同名模块收集冲突，随后发现研究内容脚本要求 CLI 初始化工作目录；立项依据脚本也不是 pytest 用例。改用各自文档规定的 CLI 入口后均通过。初次失败记录保留在任务工作区，不计为通过项。

## 复现入口

```bash
python .bensz-api/task-20261112-0704-release-v4.1.3/git-publish-release/input/pack_tracked_projects.py --tag v4.1.3
python -m pytest scripts/test_scu_master.py -q
python -m pytest tests/test_review_quality_regression.py tests/research-literature-review/test_local_bug_regression.py -q
python tests/nsfc-justification-writer/test_revision_safety.py --task-root .bensz-api/task-20261112-0704-release-v4.1.3
python tests/nsfc-research-content-writer/test_revision_safety.py --task-root .bensz-api/task-20261112-0704-release-v4.1.3
bac --root . --bac-file docs/contribution.bac verify
git diff --check
```

执行时将 pytest 缓存和临时目录指定到任务工作区，设置 `PYTHONDONTWRITEBYTECODE=1`。两个 NSFC 入口沿用自身 `skill-creator/output/` 历史产物布局，但均限制在同一个任务根目录内；未调用 skill-creator。

## 发布资产与证据

ZIP 位于 `tests/release-v4.1.3/`，不纳入 Git。本地存在已忽略、未跟踪且缺少入口文件的 `projects/FJNSF_General/` 残留目录，原始脚本会误将其打包。任务适配器从 `git ls-files` 选取 24 个有 LaTeX 入口的项目，以符号链接构成隔离输入，调用官方 `scripts/pack_release.py` 的 `main()` 生成并上传 48 个有效 ZIP；不修改用户残留目录或官方脚本。仅上传成功后才报告已发布。

任务摘要、完整区间历史、校验日志、资产大小与 SHA-256 清单、发布回执位于 `.bensz-api/task-20261112-0704-release-v4.1.3/`。发布后的远程核对回执留在该目录，不再创建晚于版本 tag 的提交。
