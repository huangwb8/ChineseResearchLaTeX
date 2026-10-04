# v4.1.1 发布前验证

日期：2026-10-04。范围为 `v4.1.0` 至本次版本提交的完整历史与当前工作区变更。

## 纳入文件

- 西电本科示例正文、图片、书目、成品 PDF、项目说明与 issue #54 验证记录。
- 根 `CHANGELOG.md` 的 4.1.1 归档、`README.md` 的本版本 ZIP 下载链接及 `Prompts.md` 的版本参数。
- `docs/contribution.bac` 的维护与发布准备证据。

初始工作区变更均属于示例维护、版本参数或贡献记录，已按职责纳入；没有待排除的无关改动。ZIP 位于 `tests/release-v4.1.1/`，不纳入 Git。

## 验证结果

| 验证 | 结果 |
| --- | --- |
| 毕业论文构建工具、安装架构、README 模板列表与 DOCX 回归 | 64 项通过 |
| research-idea、Radar 景观、Review 选文、Search 契约与 Skill 列表回归 | 158 项通过 |
| bensz-thesis 包结构 | 通过 |
| 27 个 Skill 文档契约 | 通过 |
| 23 个项目的标准 / Overleaf ZIP | 共 46 个，通过 CRC、路径与缓存排除检查 |
| 西电 ZIP 图片与元数据 | 与仓库源码一致 |
| GitHub 草稿中的 46 个资产 | 全部上传成功，文件大小及远程 SHA-256 与本地匹配 |
| BAC 与 Git 空白检查 | 发布提交前校验 |

研究类回归首次使用默认 Python 时出现 16 个失败、29 个错误，原因是 Python API 的 BSK 2.1.2 与托管 BSK 2.1.6 不一致。改用 BenszAPI 托管解释器后，同组 158 项全部通过，没有修改项目源码或系统环境。

既有西电构建中的封面 Underfull、Computer Modern 字体尺寸替代提示，以及 UCAS 代码块渲染缺口仍以 [issue #54 验证记录](issue-54-xdu-bachelor.md) 为准。本轮发布验证没有重新构建全部模板，也没有对真实在线 Overleaf 进行逐项目测试。

## 可复现命令

```bash
python -m pytest scripts/test_thesis_project_tool.py scripts/test_install_architecture.py scripts/test_update_readme_template_list.py tests/bensz-thesis/test_thesis_docx_tool.py -q -o cache_dir=.bensz-api/task-20261004-1629-release411/shared/pytest-cache
~/.bensz-skills/envs/benszapi/bin/python -m pytest tests/research-idea tests/research-literature-radar tests/research-literature-review skills/research-literature-search/tests/test_search_contract.py scripts/test_update_readme_skill_list.py -q -o cache_dir=.bensz-api/task-20261004-1629-release411/shared/pytest-cache
python packages/bensz-thesis/scripts/validate_package.py --skip-compile
python scripts/validate_skill_docs.py
python scripts/pack_release.py --tag v4.1.1
bac --root . --bac-file docs/contribution.bac verify
git diff --check
```

## 发布命令与证据

版本提交以完整版本区间为依据，最终标签 `v4.1.1` 指向版本总结提交。

```bash
git commit -F .git/COMMIT_EDITMSG
gh release create v4.1.1 --repo huangwb8/ChineseResearchLaTeX --draft --target main --title 'v4.1.1 — 西电本科模板与科研证据流程更新' --notes-file .bensz-api/task-20261004-1629-release411/git-publish-release/output/release-notes.md
python scripts/pack_release.py --tag v4.1.1 --upload
git tag -a v4.1.1 -F .bensz-api/task-20261004-1629-release411/git-commit/output/tag-message.txt
git push --atomic origin main refs/tags/v4.1.1
gh release edit v4.1.1 --repo huangwb8/ChineseResearchLaTeX --draft=false --latest
```

Release 先以草稿接收资产，公开发布在标签推送后执行；本文件记录发布前验证，不将准备状态表述为发布成功。完整历史、测试与打包日志、资产 SHA-256 清单、发布说明及最终远程核验结果保存在唯一任务目录 `.bensz-api/task-20261004-1629-release411/`。
