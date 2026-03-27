# Scripts 目录（Legacy CLI）

本目录包含 `transfer-old-latex-to-new` 的可执行脚本。

从 `v2.0.0` 开始，这些脚本的定位已经调整为：

- **可选硬编码后备**
- 主要服务“旧目录 -> 新目录”的经典迁移场景
- 不再代表这个 skill 的主工作流

如果你的任务是“按当前 ChineseResearchLaTeX 结构把模板或项目做对”，优先遵循 [../SKILL.md](../SKILL.md) 的 AI 自主编排原则，而不是先把任务强行塞进这些脚本。

## 什么时候适合用这里的脚本

适合：

- 已经有明确的 `--old` 和 `--new` 两个目录
- 需要保留 `runs/<run_id>/` 这类可追溯产物
- 希望用固定命令走一遍分析、应用、编译流程

不适合：

- 输入是 Word / PDF / Markdown / 截图 / 零散说明的混合材料
- 任务本质是 thesis / paper / cv 的结构接入或仓库级重构
- 输出需要由 AI 自主决定，而不是被固定 `runs/` 结构约束

## 脚本列表

### `run.py`

经典迁移入口，定位是 **legacy CLI**，用于已经有明确 `--old` / `--new` 目录的场景，支持：

```bash
python scripts/run.py analyze --old <旧项目> --new <新项目>
python scripts/run.py apply --run-id <run_id> --old <旧项目> --new <新项目>
python scripts/run.py compile --run-id <run_id> --new <新项目>
python scripts/run.py restore --run-id <run_id> --new <新项目>
```

可选：在 `analyze/apply/compile/restore` 时加 `--profile quick|balanced|thorough` 套用预设配置。

补充：还支持 `runs list/show/delete`。

### `migrate.sh`

对 `run.py` 的简单封装：

```bash
bash scripts/migrate.sh --old <旧项目> --new <新项目>
```

### `validate_config.py`

校验本 skill 的 `config.yaml` 是否满足 legacy CLI 所需的基础约束：

```bash
python scripts/validate_config.py
```

### `demo.py`

演示若干内部模块能力。

### `quicktest.py`

轻量快速测试入口：

```bash
python scripts/quicktest.py
```

如需跑更系统的自动化测试，可直接使用现有 pytest 用例：

```bash
pytest tests/ -q
```

注意：当前 `tests/` 目录同时包含 pytest 用例与 auto-test 会话产物，维护时要区分“自动化测试代码”和“测试记录文档”两类内容。

## 结论

如果你是在维护这个 skill，请记住：

- `SKILL.md` 才是主规范
- 这里的脚本是附属实现
- 不要反过来为了兼容脚本而限制整个 skill 的输入和输出边界
