---
name: research-literature-radar
description: 发现、筛选并长期归档重要研究论文；当用户要求按主题寻找经典、rising star、社区精选、热点或顶会/顶刊论文时使用。采用分层发现策略，调用 research-literature-search 完成其中的关键词/数据库检索，再由本 skill 负责多渠道汇总、idea-level 价值判断、论文类型分类、跨轮次跟踪和论文库归档。
metadata:
  author: Bensz Conan
---
# Research Literature Radar

## 目标

把来自不同发现渠道的候选论文转成可持续维护的研究雷达。`research-literature-search` 只是本 skill 的一个检索子步骤，负责基于显式关键词的数据库召回、字段规范化、canonical 去重和 provenance；本 skill 仍负责分层发现、跨渠道汇总、价值判断、分类、跟踪与归档。

本 skill 负责：

- 将用户目标转成筛选标准和论文类型配额；
- 对全部 canonical 候选分别判断相关性、证据深度、发表状态和身份可信度；
- 分类、排序、记录不确定性，并保留核心、辅助、待跟踪和范围外角色；
- 将入选论文映射到稳定 ID，写入论文库并维护跨轮次跟踪。

### 触发与输入概览

用户提出“找值得读的论文”“建立某主题论文雷达”“按经典/热点/顶会等类型推荐论文”或类似发现与学习需求时触发。

必填：用户选题和目标数量。可选：领域/子主题、五类论文配额（`classic`、`rising-star`、`community`、`hot`、`top-venue`）、时间窗、作者/venue 白名单、排除项、是否下载公开 PDF、笔记深度。

运行前读取 `.bensz-api/research-literature-radar/catalog.jsonl`（不存在则创建），并保留用户原始请求和运行日期。

## 流程

### 输入

按用户请求和配置文件提供必要输入；缺失信息应明确列出并停止依赖该输入的步骤。

### 执行步骤

- 仅将本 Skill 的设计缺陷（流程漏判、输入契约不完整或环境假设错误）视为可上报 bug；用户数据错误、第三方服务抖动、用户主动改源码和模型偶发波动不属于此范围。
- 发现设计缺陷时先脱敏记录到 `~/.bensz-skills/bugs/`，当前任务继续；只有用户明确要求公开上报时，才使用本机 `gh api` 直传，不 clone 仓库。
- 不收集用户名、主机名、工作目录、密钥、令牌、Cookie 或其它无关隐私；不得直接修改用户本地已安装 Skill 的源代码来“顺手修 bug”。

版本唯一来源为同目录 `config.yaml:skill_info.version`；本文件只描述稳定工作契约，不重复易变配置。

不要把论文发现简化成单一关键词检索。根据用户选题和目标数量，组合以下五类渠道；每类都可以使用联网检索、研究者脉络或社区信号，但必须记录其来源和用途：

- **经典论文**：定位领域奠基者、明星研究者、综述、奖项和公认里程碑，再查找其代表性工作。
- **rising-star 论文**：寻找近 3–5 年持续突破的作者、实验室或研究线，关注尚未广为人知但影响快速上升的研究者。
- **社区精选**：检查 Hugging Face Daily/Weekly/Monthly Papers、Import AI、研究者通讯、公众号/X 账号和可信整理页。
- **偶然的热点论文**：关注近期发表后因讨论度、代码传播、新闻或社交平台而受到关注的论文，即使作者并不知名。
- **顶会/顶刊近期论文**：仅在用户选题足够窄时重点使用，结合明确的 venue 和时间窗，避免宽主题造成无穷候选。

`research-literature-search` 负责其中“基于关键词检索学术数据库”的小步骤；经典作者脉络、社区精选和热点信号不能假设会自动出现在该检索 bundle 中。

### 首选：调用 search 后端

当分层策略需要关键词/数据库召回时，调用 `research-literature-search` 的 `run`，为其提供合法的 `topic` 和 5–25 条显式查询；随后调用其 `validate`。只接受 `manifest.json` 的 `status` 为 `success` 或 `partial_success` 的 bundle。没有需要数据库检索的渠道时，不得为了形式强行调用；但必须说明使用了哪些其它发现渠道。

将以下文件作为只读输入保存到本轮 radar run：

```text
manifest.json
candidates_deduped.jsonl
provenance.jsonl
dedupe_map.json
```

候选必须符合 `rls.paper.v1`。保留 manifest、contract version、artifact hash、canonical 候选数量和 search source path，便于追溯。若实际调用了 search 但 bundle 校验失败、没有合法查询或 search skill 不可发现，应停止该检索子步骤并报告原因；不能静默改用另一套内嵌 provider。其它分层渠道仍可独立记录为补充发现，但不得伪装成 search 结果。

### 补充发现信号

社区精选、奖项、研究者整理、代码传播或新闻讨论等非标准数据库信号可以作为补充证据，但必须：

- 记录 URL、访问日期、来源用途和对应论文身份；
- 映射到已有 canonical 候选，或作为明确标记的待确认候选；
- 不伪装成 search provider 结果，不覆盖 search 的 canonical 顺序和去重结论。

当补充信号产生新论文时，使用本 skill 的稳定身份键与 catalog 比对；相似但无法确认的记录标记 `possible_duplicate`，不得静默合并。

对全部 canonical 候选先建立 landscape，再对可能进入核心集者评分。每条记录包含 `record_id`、`canonical_rank`、`role`、`cluster`、`relevance`、`evidence_depth`、`publication_status`、`identity_confidence`、`use_cases`、`reason`、`uncertainties` 和 `source_refs`。标题可用于发现、聚类和 watchlist；摘要可支持相关性与作者自报判断；方法、结果和等价性强结论必须匹配全文证据。预印本状态与来源数量不能替代相关性判断。

由 AI 批量聚类并填写简短判断草稿，再运行 `scripts/build_landscape.py --bundle <search-bundle> --draft <draft.jsonl> --output <literature-landscape.jsonl> --summary <landscape-summary.json>` 做 manifest/hash、全量覆盖、ID 唯一、枚举、canonical 顺序与计数对账。确定性脚本不得硬编码领域关键词或替 AI 判定科学价值。

对核心候选按 0–5 分记录：`conceptual_novelty`、`simplicity`、`surprise`、`generality`、`unification`、`new_primitive`、`follow_up_potential`、`practical_impact`。证据质量单列为 `confidence`，不混入“有趣程度”。

为每篇核心候选记录总分、两句理由、关键证据、思想标签和不确定性；其余候选仍保留在 landscape，不能缩成落选总数。思想标签可使用：`problem-reformulation`、`unexpected-simplicity`、`hidden-equivalence`、`assumption-revisit`、`new-measurement`、`failure-revealing`、`new-primitive`、`cross-domain-transfer`。

用配额检查研究线覆盖，但不为填满配额选择低质量论文；再按总分、思想标签/年份/作者多样性形成精而少的核心集。辅助或待跟踪条目成为关键近邻时保留 Search record ID，并可新增 R 锚点和解读历史，不重新去重。

`scripts/catalog.py` 提供不依赖网络的 ID 生成、标题标准化、索引加载和重复判定；`scripts/validate_layout.py` 在交付前检查运行级文件是否错误写入 `docs/papers/` 根目录。脚本不会下载或删除文件。

### 输出

每轮先加载 catalog，再消费已验证的 search bundle。重复项只更新来源、版本、评分或跟进记录；只有真正新论文才创建目录。将 `literature-landscape.jsonl`、`landscape-summary.json`、`discovery.md`、`selection.md`、`dedup-report.md` 和运行摘要写入同一 `runs/<run-id>/`，并明确 canonical 数 = core + supporting + watchlist + out_of_scope。

交付前确认：每个实际使用的 search manifest 可消费、canonical hash 与数量可追溯；landscape 恰好覆盖每个 canonical record ID；五类渠道的适用性和覆盖情况有说明。一个可靠来源通常足以确认身份；只有元数据冲突、版本合并、疑似重复或决定性近邻才要求额外核对。ID、metadata、catalog、raw manifest 与内部路径一致；根目录 `index.md` 已包含每篇新增论文；`docs/papers/` 根目录没有运行级文件。

### 输出管理

目录 ID 使用 `<first-author-full-name>-<year>-<keyword>`：首位作者全名、四位年份和可识别工作/方法关键词均为 ASCII 小写并以单个连字符分隔。关键词优先使用公认简称；无稳定简称时使用标题短 slug。arXiv、DOI、OpenReview 等外部编号不能作为目录主名，必须写入 `identifiers`。

身份比对顺序为 DOI → arXiv/OpenReview → 其它稳定 ID → 标准化标题+首位作者+年份。预印本与正式版合并并保留版本链接；冲突时在关键词末尾追加稳定短哈希。已有笔记不覆盖，只补充缺失字段并在 `history` 写明变更原因。

```text
docs/papers/
└── <friendly-id>/
    ├── raw/                       # 公开 PDF、HTML、metadata、manifest
    └── <friendly-id>.md           # 学习笔记

.bensz-api/research-literature-radar/
├── catalog.jsonl                  # 跨轮次论文索引
└── runs/<run-id>/                 # run.yaml、search 交接包、筛选与去重报告
```

`docs/papers/` 只存论文实体及其原始材料/学习笔记；运行级配置、manifest、筛选报告、日志和去重报告统一写入 `.bensz-api/research-literature-radar/`。原始文件用外部标识命名，可记录 SHA-256，禁止静默覆盖。

`catalog.jsonl` 每行至少记录 `id,title,authors,year,venue,status,paper_types,tags,identifiers,sources,files,scores,confidence,first_seen_run,last_seen_run,history`，且 `id` 必须与论文目录名和笔记文件名一致。

### 校验

完成后执行 Skill 已有的静态检查、脚本验证或人工复核，并记录通过标准。

### 失败与恢复

保留错误证据和已完成产物；仅在输入、环境或外部依赖恢复后从最近的失败步骤重试。

## 约束

遵守以下公共约束，并执行本 Skill 的专属边界。

### 公共硬约束

- 任务需要落盘时，使用唯一的 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/` 根目录；共享材料放入 `shared/`，Skill 专属材料放入该 Skill 的 `input/`、`output/`、`log/`。
- 正式交付物、源代码和正式计划按项目约定保存，不写入任务工作区；未经授权不覆盖、删除、迁移或远程写入。
- 项目维护变更检查 BAC 可用性并记录需求、AI 产出、工具结果、文件改动和验证摘要；BAC 只做过程审计，不替代署名、责任或合规判断。
- 不记录 API Key、访问令牌、密码、Cookie、环境/凭据文件、私有 Prompt、身份信息、本地用户名、主机名或不必要的大体积原始数据。
- 文件路径必须规范化并限制在授权项目范围内；外部 URL、子进程和网络访问遵循最小权限，防止路径遍历、SSRF 和命令注入。
- Skill 版本唯一记录在自身 `config.yaml:skill_info.version`；公开 API、协议、目录或配置变更同步文档与 `CHANGELOG.md`。
- 仅将 Skill 或 Bensz 基础设施本身的设计缺陷交给 `bensz-collect-bugs`；先脱敏写入 `~/.bensz-skills/bugs/`，当前任务不中断，只有用户明确要求才公开上报，禁止直接修改用户已安装的 Skill 源码。
<!-- End of canonical common constraints. -->

### Skill 专属约束

不得超出本 Skill description 和上方流程所声明的范围；不将未验证的信息伪装成确定结论。
