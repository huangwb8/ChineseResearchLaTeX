---
name: research-literature-search
description: 当用户需要检索候选论文、建立可审计文献池或为下游证据任务准备候选文献时使用。也适用于 research-literature-review 的检索依赖。
metadata:
  author: Bensz Conan
---

# Research Literature Search

## 目标

将主题和 5–25 条查询转换为可复核的候选文献 bundle。负责召回、字段规范化、canonical 去重、来源审计和可选摘要补全；不负责评分、纳入/排除、子主题、配额、综述写作、BibTeX 或 PDF/Word 导出。`research-literature-review` 必须消费本 Skill 的 manifest 和 canonical 候选，不得复制 provider 或重做去重。

## 流程

### 输入

- 必需：`topic` 与显式查询 JSON（`--query-file`/`--queries`）；支持 `{"queries": [...]}`、对象数组或字符串数组。
- 空查询剔除；有效查询默认 5–25 条，不满足即 fail-closed。
- 可选：`domain`、年份/文献类型/预印本过滤、provider 顺序、每查询/总量上限、`scope_root`。
- 输出必须位于调用方 `scope_root` 内；拒绝路径穿越和 manifest 外部绝对路径。

### 执行步骤

```bash
python3 skills/research-literature-search/scripts/search_runner.py run --topic "HER2 antibody-drug conjugates in breast cancer" --query-file ./queries.json --output-dir ./.bensz-api/search-bundle
python3 skills/research-literature-search/scripts/search_runner.py enrich-abstracts --input selected_papers.jsonl --output selected_papers_enriched.jsonl
python3 skills/research-literature-search/scripts/search_runner.py validate --bundle ./.bensz-api/search-bundle
```

`run` 默认不补全全量摘要；选文后按需执行 `enrich-abstracts`。provider 按 `provider_priority` 执行 priority-fallback-topup，达到约 70% 阈值即停止，不承诺全 provider union；`mcp`/`duckduckgo` 在纯 Python runner 中记为 `skipped/host tool required`。每次尝试写入 `attempts`、Search Log、`retrieval_strategy` 和 `topup_threshold`。

### 输出

`manifest.json` 是唯一入口，每次运行使用独立目录：

```text
manifest.json
candidates_raw.jsonl          # 脱敏的最小 provider 信封
candidates_normalized.jsonl  # rls.paper.v1，去重前
candidates_deduped.jsonl     # canonical 候选池
provenance.jsonl              # provider/query/rank 映射
dedupe_map.json               # 合并边与选择依据
search_log.json               # 可读审计日志
```

候选必须符合 `rls.paper.v1`：非空 `title`、字符串数组 `authors`、`identifiers`、`abstract_status`、`publication`、`sources`、`query_matches`、`quality_warnings`，并保留旧扁平字段；缺失值只能用 `null`/`[]`。manifest `status` 仅为 `success`、`partial_success`、`failed`；review 只接受前两者并校验 hash、schema、数量。

### 输出管理

临时产物写入任务工作区，正式交付物按项目约定保存；未经授权不覆盖、删除或远程写入已有文件。所有路径必须限制在授权项目内。

### 校验

运行 Skill 已有的静态检查、脚本验证或人工复核，并记录通过标准。manifest 保存查询 SHA-256、provider policy、attempts、截断、去重参数、缓存模式、版本和 artifact hash。

### 失败与恢复

provider 返回 `null`、非对象或嵌套 source 为 `null` 时跳过/保留并记录计数或 warning；无合法候选返回 `no_valid_candidates`，不得静默丢弃。preprint 按领域 profile（`auto`→computer_science/mathematics/biology/medicine/general）标记并审计，搜索层不认证结论。旧 `title/year/id` 仅经显式 legacy adapter 并附 `legacy_adapted` warning；新增 provider/union 策略需升级 contract。

## 约束

- JSON 使用 UTF-8、稳定排序和确定性序列化；同夹具/配置下顺序可比较。
- 不写入 API key、Cookie、完整响应或其它凭据；不得将未验证信息伪装为确定结论。

<!-- BEGIN COMMON CONSTRAINTS -->
<!-- Source-Hash: sha256:15120201e9e0c7569517261d57ecefb63ac279c26ed13876f8e95b6dc35854d3 -->
<!-- Template-ID: skill-common-constraints; Template-Version: 1; Sync-Policy: exact-block -->

### 公共硬约束

本块由 `docs/templates/skill-common-constraints.md` 统一维护；每个 `SKILL.md` 的 `## 约束` 必须逐字同步本块，不得在副本中改写公共规则。

- 任务需要落盘时，使用唯一的 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/` 根目录；共享材料放入 `shared/`，Skill 专属材料放入该 Skill 的 `input/`、`output/`、`log/`。
- 正式交付物、源代码和正式计划按项目约定保存，不写入任务工作区；未经授权不覆盖、删除、迁移或远程写入。
- 项目维护变更检查 BAC 可用性并记录需求、AI 产出、工具结果、文件改动和验证摘要；BAC 只做过程审计，不替代署名、责任或合规判断。
- 不记录 API Key、访问令牌、密码、Cookie、环境/凭据文件、私有 Prompt、身份信息、本地用户名、主机名或不必要的大体积原始数据。
- 文件路径必须规范化并限制在授权项目范围内；外部 URL、子进程和网络访问遵循最小权限，防止路径穿越、SSRF 和命令注入。
- Skill 版本唯一记录在自身 `config.yaml:skill_info.version`；公开 API、协议、目录或配置变更同步文档与 `CHANGELOG.md`。
- `bensz-collect-bugs` 是一个 Agent Skill；仅将 Bensz Agent Skill 或 Bensz 基础设施本身的设计缺陷交给它。先脱敏写入 `~/.bensz-skills/bugs/`，当前任务不中断，只有用户明确要求才公开上报，禁止直接修改用户已安装的 Skill 源码。

<!-- End of canonical common constraints. -->
<!-- END COMMON CONSTRAINTS -->

### Skill 专属约束

不得超出本 Skill description 和上方流程所声明的范围；不将未验证的信息伪装成确定结论。
