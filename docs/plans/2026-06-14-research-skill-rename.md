# Research 系列 Skill 重命名计划

**创建时间**: 2026-06-14  
**状态**: 设计草案，待确认后执行  
**目标**: 将早期命名的研究类 skills 收敛为 `research-*` 系列，同时保证旧 skill 名在过渡期仍能触发新 skill，并通过 `install-bensz-skills` 自动清理系统级旧目录。

---

## 背景

当前研究类 skills 已经形成一条相对完整的研究工作流，但命名来源不统一：

- `get-review-theme`
- `guide-updater`
- `check-review-alignment`
- `make-research-plan`
- `systematic-literature-review`
- `research-idea`

其中 `research-idea` 已经使用 `research-*` 命名，并且会依赖 `get-review-theme` 与 `systematic-literature-review` 做查新。当前相关依赖写在 [research-idea/config.yaml](../../skills/research-idea/config.yaml#L24)、[research-idea/SKILL.md](../../skills/research-idea/SKILL.md#L26) 等位置。

本次计划的核心不是重写这些 skills 的能力，而是做一次低风险的身份迁移：

1. 新 skill 目录和 frontmatter 统一使用 `research-*` 命名。
2. 旧名作为 legacy alias 保留在新 skill 的触发描述、README 与迁移文档中。
3. 旧目录不再保留为 wrapper，避免和安装器的 legacy 清理机制冲突。
4. `install-bensz-skills` 将旧名加入 `legacy_skill_names`，安装新版本时自动删除系统级旧 skill 目录。该机制当前由 [install-bensz-skills/config.yaml](../../../../winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/config.yaml#L13) 与 [remove_legacy_skills.py](../../../../winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/scripts/remove_legacy_skills.py#L11) 支持。

## 推荐命名

| 旧名 | 推荐新名 | 说明 |
| --- | --- | --- |
| `get-review-theme` | `research-topic-extractor` | 强调从资料中提取研究主题、关键词与核心问题，比 `research-theme` 更明确。 |
| `guide-updater` | `research-guide-updater` | 保留 updater 语义，纳入研究工作流命名体系。 |
| `check-review-alignment` | `research-citation-check` | 实际核心是综述引用语义核查，比 alignment 更容易理解和记忆。 |
| `make-research-plan` | `research-plan` | 简短，对齐 `research-idea`，表达生成实验设计、分析策略和技术路线。 |
| `systematic-literature-review` | `research-literature-review` | 保留文献综述语义，同时并入 `research-*` 系列。 |
| `research-idea` | 保持不变 | 已符合系列命名。 |

## 非目标

第一阶段不做以下事情：

- 不重命名历史工作目录，例如 `.systematic-literature-review/`、`.make-research-plan/`、`.check-review-alignment/`。
- 不修改历史输出文件名、历史 examples、历史 CHANGELOG 记录中的旧名，除非它们会影响当前触发或运行。
- 不保留旧目录作为 wrapper skill。
- 不借重命名顺手重构业务逻辑、脚本流程或输出格式。

这些约束可以显著降低迁移风险。运行产物目录已经被脚本、README、历史输出和其它 skill 的识别逻辑引用，例如旧名 `systematic-literature-review` 的隐藏目录配置已迁移到 [research-literature-review/config.yaml](../../skills/research-literature-review/config.yaml#L285)，旧名 `make-research-plan` 的隐藏目录配置已迁移到 [research-plan/config.yaml](../../skills/research-plan/config.yaml#L12)。

## 兼容策略

### 触发兼容

新 skill 的 `SKILL.md` frontmatter `description` 必须显式包含旧名。例如：

```yaml
name: research-literature-review
description: 当用户明确要求"做系统综述/文献综述/related work/相关工作/文献调研"，或要求使用旧名 systematic-literature-review skill 时，使用本 skill。...
```

理由：Codex / Claude 的 skill 触发主要依赖 `name + description`。旧名如果只放在 `metadata.keywords`、README 或 CHANGELOG 中，触发稳定性不够。

### 依赖兼容

跨 skill 依赖需要优先使用新名，同时在脚本或说明中保留旧名 fallback：

- `research-idea`：优先依赖 `research-topic-extractor` 与 `research-literature-review`，过渡期允许发现 `get-review-theme` 与 `systematic-literature-review`。
- `research-citation-check`：渲染依赖优先指向 `research-literature-review`，过渡期允许 fallback 到 `systematic-literature-review`。
- `nsfc-justification-writer` 中对 `systematic-literature-review` 结果目录的只读识别暂不改产物目录，只在文案中补充“由 `research-literature-review` 生成，历史目录名仍为 `.systematic-literature-review/`”。

### 安装兼容

`install-bensz-skills` 已经支持安装前删除 legacy skill 目录。迁移时需要在 `legacy_skill_names` 增加：

```yaml
legacy_skill_names:
  - "get-review-theme"
  - "guide-updater"
  - "check-review-alignment"
  - "make-research-plan"
  - "systematic-literature-review"
```

注意：旧名进入 legacy 清理名单后，不应继续作为真实安装目录存在，否则安装器会在“完整安装”时清理旧目录。旧名兼容必须由新 skill 的触发描述和别名说明承担。

## 修改范围

### Skill 目录重命名

使用 `git mv`：

```bash
git mv skills/get-review-theme skills/research-topic-extractor
git mv skills/guide-updater skills/research-guide-updater
git mv skills/check-review-alignment skills/research-citation-check
git mv skills/make-research-plan skills/research-plan
git mv skills/systematic-literature-review skills/research-literature-review
```

### 每个重命名 skill 内部

每个新目录至少检查并更新：

- `SKILL.md`
  - frontmatter `name`
  - frontmatter `description`
  - `metadata.short-description`
  - `metadata.keywords`
  - 旧名兼容说明
  - 相邻 skill 边界说明
- `config.yaml`
  - `skill_info.name`
  - `skill_info.description`
  - 依赖 skill 名称
  - 如有版本变更，按语义化版本递增
- `README.md`
  - 快速开始示例
  - FAQ
  - 旧名迁移说明
  - 命令行路径示例
- `CHANGELOG.md`
  - 记录重命名、旧名兼容与安装器 legacy 清理策略
- `scripts/`
  - argparse 描述文案
  - skill 名字符串
  - 默认路径字符串
  - 依赖检测逻辑
- `references/`
  - 非历史事实的旧名引用
  - 相邻 skill 流程说明

### 跨 skill 引用

需要重点检查：

- [research-idea/SKILL.md](../../skills/research-idea/SKILL.md#L26)
- [research-idea/config.yaml](../../skills/research-idea/config.yaml#L24)
- [research-idea/scripts/init_workspace.py](../../skills/research-idea/scripts/init_workspace.py#L46)
- [research-idea/references/novelty-check.md](../../skills/research-idea/references/novelty-check.md#L7)
- [research-citation-check/config.yaml](../../skills/research-citation-check/config.yaml#L32)
- [research-citation-check/scripts/run_ai_alignment.py](../../skills/research-citation-check/scripts/run_ai_alignment.py#L201)
- [research-citation-check/scripts/runtime_utils.py](../../skills/research-citation-check/scripts/runtime_utils.py#L184)
- [nsfc-justification-writer/config.yaml](../../skills/nsfc-justification-writer/config.yaml#L185)
- [nsfc-justification-writer/scripts/core/review_integration.py](../../skills/nsfc-justification-writer/scripts/core/review_integration.py#L5)

### 项目级文档

同步更新：

- [README.md](../../README.md#L262)
- [skills/README.md](../../skills/README.md#L13)
- [CHANGELOG.md](../../CHANGELOG.md#L1)

建议在根级 README 和 `skills/README.md` 中增加一个短迁移表：

| 旧名 | 新名 | 兼容状态 |
| --- | --- | --- |
| `get-review-theme` | `research-topic-extractor` | 旧名 prompt 暂时兼容，旧目录安装时清理 |
| `guide-updater` | `research-guide-updater` | 旧名 prompt 暂时兼容，旧目录安装时清理 |
| `check-review-alignment` | `research-citation-check` | 旧名 prompt 暂时兼容，旧目录安装时清理 |
| `make-research-plan` | `research-plan` | 旧名 prompt 暂时兼容，旧目录安装时清理 |
| `systematic-literature-review` | `research-literature-review` | 旧名 prompt 暂时兼容，旧目录安装时清理 |

### 安装器

更新外部 skills 仓库中的 `install-bensz-skills`：

- [config.yaml](../../../../winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/config.yaml#L13)：追加 5 个旧名到 `legacy_skill_names`。
- [CHANGELOG.md](../../../../winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/CHANGELOG.md#L1)：记录本次 legacy 名单更新。
- 如版本号需要递增，更新 [config.yaml](../../../../winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/config.yaml#L4)、README 与 SKILL 文档。

## 执行步骤

### 阶段 1：迁移前审计

1. 运行引用盘点：

   ```bash
   rg -n "get-review-theme|guide-updater|check-review-alignment|make-research-plan|systematic-literature-review" \
     skills README.md CHANGELOG.md docs
   ```

2. 记录旧名引用，按类型分组：
   - 必须替换为新名的当前口径。
   - 必须保留为 legacy alias 的兼容口径。
   - 可保留的历史记录。

3. 运行安装器现有测试，确认迁移前基线：

   ```bash
   pytest /Volumes/2T01/winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/tests/test_install.py -q
   ```

### 阶段 2：目录和元信息迁移

1. 使用 `git mv` 重命名 5 个目录。
2. 更新 5 个新 skill 的 `SKILL.md` 与 `config.yaml`。
3. 在每个新 skill 的 README 增加“旧名兼容”小节。
4. 保留历史工作区名不变，但在 README 中说明这是稳定产物目录，不等同于 skill 新名称。

### 阶段 3：依赖和脚本迁移

1. `research-idea` 依赖改为新名，保留旧名 fallback。
2. `research-citation-check` 渲染依赖改为新名，保留旧名 fallback。
3. 搜索脚本中的硬编码路径和 argparse 描述，避免继续把旧名作为主口径。
4. 对只读识别历史产物目录的逻辑不做破坏性修改。

### 阶段 4：安装器 legacy 清理

1. 在 `install-bensz-skills/config.yaml` 追加旧名。
2. 运行 legacy 清理 dry-run：

   ```bash
   python3 /Volumes/2T01/winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/scripts/remove_legacy_skills.py --dry-run
   ```

3. 运行安装器测试：

   ```bash
   pytest /Volumes/2T01/winE/PythonCloud/Agents/pipelines/skills/install-bensz-skills/tests/test_install.py -q
   ```

### 阶段 5：文档同步

1. 更新根级 README 技能表。
2. 更新 `skills/README.md` 推荐工作流。
3. 更新根级 CHANGELOG。
4. 更新相关 skill 的 CHANGELOG。
5. 检查所有新链接是否指向新目录。

### 阶段 6：触发与安装验证

在临时目录中模拟安装，不污染根目录：

```bash
mkdir -p tests/research-skill-rename
```

建议验证项：

- 完整安装后系统级目录中只有新名，没有旧名。
- `--skill research-literature-review` 能只安装新名。
- 旧名目录存在时，完整安装会删除旧名目录。
- 当用户 prompt 写“请使用 systematic-literature-review skill”时，`research-literature-review` 的 description 足以触发。
- 当用户 prompt 写“请使用 get-review-theme skill”时，`research-topic-extractor` 的 description 足以触发。
- `research-idea` 能发现新依赖。
- `research-citation-check` 能发现新渲染依赖。

## 验证矩阵

| 验证项 | 命令或方法 | 通过标准 |
| --- | --- | --- |
| 旧名引用盘点 | `rg` | 旧名只出现在 legacy alias、迁移说明、历史记录、兼容 fallback 中。 |
| 安装器测试 | `pytest install-bensz-skills/tests/test_install.py -q` | 全部通过。 |
| legacy 清理 dry-run | `remove_legacy_skills.py --dry-run` | 会列出旧目录清理动作，不误删新目录。 |
| 新 skill 可安装 | `install.py --skill <new-name>` | 目标平台出现新名目录。 |
| 旧 skill 可清理 | 预置旧名目录后完整安装 | 旧名目录被删除，新名目录保留。 |
| `research-idea` 依赖 | 运行依赖检查脚本或 smoke prompt | 优先发现新名，旧名只作 fallback。 |
| `research-citation-check` 依赖 | 准备已有综述目录，执行 prepare/render smoke | 能找到 `research-literature-review` 渲染脚本。 |
| 文档链接 | `rg` + 手动抽查 | README 与 skills/README 链接均指向新目录。 |

## 回滚方案

如果迁移后发现触发或安装问题：

1. 优先修复新 skill 的 `description`，把旧名触发语写得更直接。
2. 如果是依赖发现问题，补充 alias fallback，不恢复旧目录。
3. 如果是安装器误删问题，先从 `legacy_skill_names` 临时移除受影响旧名，并补测试。
4. 只有当新名目录本身导致大面积不可用时，才使用 `git mv` 回滚目录名。

## 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 旧名 prompt 不能触发新 skill | 用户习惯受损 | 旧名必须进入 `description`，并做触发测试。 |
| 安装器删除旧目录后没有安装新目录 | 用户失去该 skill | 确认新目录已在远程源 `skills/` 中，完整安装测试必须覆盖。 |
| 运行目录改名导致历史产物不可识别 | 破坏历史工作流 | 第一阶段不改 `.systematic-literature-review/` 等运行目录。 |
| 脚本硬编码旧 skill 名 | 依赖检查失败 | 统一做 alias-aware 依赖解析。 |
| 文档大量旧名残留 | 用户混乱 | 当前文档主口径改新名；历史 CHANGELOG 保留旧名。 |

## 最小可接受交付

一次合格的第一阶段迁移至少应完成：

- 5 个 skill 目录完成 `research-*` 重命名。
- 5 个新 skill 的 `SKILL.md` description 显式兼容旧名。
- `research-idea` 与 `research-citation-check` 的依赖更新为新名并保留旧名 fallback。
- `install-bensz-skills` 的 `legacy_skill_names` 包含 5 个旧名。
- 根级 README、`skills/README.md`、CHANGELOG 已同步。
- 安装器测试和关键依赖 smoke 测试通过。

## 建议执行顺序

1. 先迁移 `research-literature-review`，因为它是被依赖最多的核心 skill。
2. 再迁移 `research-topic-extractor`，随后更新 `research-idea`。
3. 再迁移 `research-citation-check`，处理它对文献综述渲染脚本的依赖。
4. 再迁移 `research-plan` 与 `research-guide-updater`。
5. 最后更新安装器 legacy 清理名单和总文档。

这个顺序可以让核心依赖链先稳定下来，降低后续并发替换带来的排查成本。
