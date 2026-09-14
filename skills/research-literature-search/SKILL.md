---
name: research-literature-search
description: 当用户只需要检索候选论文、建立可审计文献池、为研究选题或其它下游证据任务准备候选文献时使用。执行查询契约校验、多源检索、规范化、去重、来源追踪并输出可验证 manifest bundle；不负责相关性评分、最终选文、综述写作、BibTeX 或 PDF/Word 导出。也可被 research-literature-review 作为必需依赖调用。
metadata:
  author: Bensz Conan
---
# Research Literature Search

### 定位与边界

本 Skill 是文献检索生产者：把主题和 5–25 条查询转换为一个可复核的候选文献 bundle。它只负责召回、字段规范化、canonical 去重、来源审计和可选摘要补全；评分、纳入/排除判断、子主题、参考文献配额、正文和导出交给下游 Skill。

`research-literature-review` 必须通过本 Skill 的 manifest 和 canonical 候选消费检索结果，不得在阶段 1/2 复制 provider 或再次改变 canonical 去重结果。

### 输入契约

- 必需：`topic` 和显式查询 JSON（`--query-file`/`--queries`）。支持 `{"queries": [...]}`、对象数组、字符串数组。
- 空查询会剔除；有效查询默认 5–25 条，数量不满足时 fail-closed。
- 可选：`domain`、年份/文献类型/预印本过滤、provider 顺序、每查询/总量上限、scope root。
- 所有输出路径必须位于调用方指定的 scope root 内；不接受路径穿越或 manifest 中的外部绝对路径。

## 流程

### 输入

按用户请求和配置文件提供必要输入；缺失信息应明确列出并停止依赖该输入的步骤。

### 执行步骤

```bash
# 独立检索，生成 manifest bundle
python3 skills/research-literature-search/scripts/search_runner.py run \
  --topic "HER2 antibody-drug conjugates in breast cancer" \
  --query-file ./queries.json \
  --output-dir ./.bensz-api/search-bundle

# 对选文后的 JSONL 做可选摘要状态整理
python3 skills/research-literature-search/scripts/search_runner.py enrich-abstracts \
  --input selected_papers.jsonl --output selected_papers_enriched.jsonl

# 校验交接包（review 消费前必须通过）
python3 skills/research-literature-search/scripts/search_runner.py validate \
  --bundle ./.bensz-api/search-bundle
```

`run` 默认不对全量候选强制补全。使用 `enrich-abstracts` 对 selected 或指定子集处理；输出 `abstract_status`、`abstract_provenance`、缺失摘要 warning 和统计。综述仍在选文后调用该能力，以保持请求量和选文行为兼容。

### 输出

每次运行都生成独立目录，`manifest.json` 是唯一入口：

```text
manifest.json
candidates_raw.jsonl          # 脱敏的最小 provider 命中信封
candidates_normalized.jsonl  # rls.paper.v1，去重前
candidates_deduped.jsonl     # canonical 候选池，下游默认读取
provenance.jsonl              # provider/query/rank 到 canonical 的映射
dedupe_map.json               # 合并边及 canonical 选择依据
search_log.json               # 兼容旧 Search Log 字段的可读日志
```

候选 schema 版本为 `rls.paper.v1`，必须有非空 `title`、字符串数组 `authors`、`identifiers`、`abstract_status`、`publication`、`sources`、`query_matches` 和 `quality_warnings`；同时在边界生成 `doi/abstract/venue/year/url/source` 等旧扁平字段。缺失值用 `null`/`[]`，不填虚构占位文本。

manifest 的 `status` 只有三种语义：`success`（完整成功）、`partial_success`（仍有可用候选但存在失败/跳过/截断/字段缺失）、`failed`（输入、路径、provider 或产物不可消费）。`research-literature-review` 只接受前两者，并校验 artifact hash、schema 和数量。

### 输出管理

临时产物写入任务工作区，正式交付物写入项目约定位置；未经授权不覆盖或删除已有文件。

### 校验

完成后执行 Skill 已有的静态检查、脚本验证或人工复核，并记录通过标准。

### 失败与恢复

默认行为锁定为 OpenAlex 主力；结果不足时按策略补充 Semantic Scholar/Crossref。`mcp` 与 `duckduckgo` 在纯 Python runner 中记录为 `skipped/host tool required`，不能伪装成功。每次尝试都写入 manifest `attempts` 和 Search Log。新 provider 或 union 召回策略需要升级 contract，不在本版本隐式引入。manifest contract 常量由独立命名的 `rls_contract.py` 提供，避免被下游 review skill 的同名模块遮蔽。

Provider 返回 `null` 结果或列表中混入 `null` / 非对象条目时，边界层必须跳过无效条目而不能调用 `.get()`；合法条目继续参与召回、规范化和去重。每次尝试在 `attempts` 中记录 `empty_records` / `invalid_records`，运行级 `counts` 同步累计并写入 warning。若没有任何合法候选，使用 `no_valid_candidates` 说明是数据无效导致的失败；不得静默丢弃或把空记录计入召回配额。

合法候选的嵌套 provider 元数据也必须按类型防御；例如 OpenAlex 的 `primary_location.source` 为 `null` 时，保留候选、令 `venue` 为 `null` 并加入 `missing_venue` 质量 warning，不得让单条记录中断整个 bundle。

## 约束

- JSON 使用 UTF-8、稳定排序和确定性序列化；相同夹具/配置下候选顺序可比较。
- manifest 保存查询文件 SHA-256、provider policy、attempts、截断数、去重参数、缓存模式、版本和每个 artifact hash。
- 旧 `title/year/id` 记录只能通过显式 legacy adapter 适配，并附加 `legacy_adapted` warning；不能冒充新 schema。
- 不把 API key、Cookie、完整响应或其它凭据写入 raw/provenance/log。

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
