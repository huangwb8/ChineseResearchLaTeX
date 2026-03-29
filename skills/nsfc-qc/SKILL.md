---
name: nsfc-qc
version: 1.2.0
description: 当用户明确要求"标书QC/质量控制/润色前质检/引用真伪核查/篇幅与结构检查"时使用。对 NSFC 标书进行只读质量控制：并行多线程独立检查文风生硬、引用假引/错引风险、篇幅与章节分布、逻辑清晰度等，最终输出标准化 QC 报告；中间文件默认归档到“交付目录内的隐藏工作区（.nsfc-qc/）”，并兼容 legacy `.nsfc-qc/`。
author: Bensz Conan
metadata:
  author: Bensz Conan
  short-description: NSFC 标书只读 QC（多线程 + 标准化报告）
  keywords:
    - nsfc-qc
    - 标书质检
    - 质量控制
    - 引用核查
    - 篇幅检查
    - 逻辑通顺
    - 文风优化建议
  triggers:
    - QC
    - 质量控制
    - 质检
    - 标书检查
    - 引用核查
    - 假引
    - 错引
    - 篇幅
    - 章节分布
config: skills/nsfc-qc/config.yaml
references: skills/nsfc-qc/references/
---

# NSFC 标书质量控制

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 只读 QC：不修改 `.tex/.bib/.cls/.sty`
- 目标是产出标准化 QC 报告，而不是“顺手帮用户改文”
- 推荐布局：`deliver_dir/` 放交付物，`deliver_dir/.nsfc-qc/` 放工作区

## 输入

最少需要：

- `project_root`

建议同时提供：

- `main_tex`，默认 `main.tex`
- `threads`，默认读 `config.yaml`
- `execution`，默认 `serial`
- `deliver_dir`，推荐显式给，便于实例隔离

## 输出

标准交付物：

- `{run_dir}/final/nsfc-qc_report.md`
- `{run_dir}/final/nsfc-qc_metrics.json`
- `{run_dir}/final/nsfc-qc_findings.json`
- `{run_dir}/final/validation.json`

常见预检产物：

- `precheck.json`
- `citations_index.csv`
- `tex_lengths.csv`
- `reference_evidence.jsonl`
- `reference_evidence_summary.json`

## 硬规则

- 禁止写入标书源文件。
- 文献真实性检查必须有证据链；不确定时标记 `uncertain`。
- 元数据获取是必选项：引用真伪核查必须联网抓取论文 metadata 并做 URL/title 比对。
- `nsfc-qc` 不负责正文改写；只负责发现问题与给出建议。

## 主流程

### 1. 定位 run 目录

- 优先用实例隔离布局：
  - `deliver_dir`
  - `workspace_dir={deliver_dir}/.nsfc-qc`
  - `run_dir={workspace_dir}/runs/{run_id}`
- 只有用户明确要求 legacy 时才退回 `project_root/.nsfc-qc/`

### 2. 只读预检

- 自动检测主 tex
- 检查引用 key 是否存在
- 检查 `.bib` 字段完整性
- 生成引用证据包：Crossref / arXiv / Unpaywall 等 metadata + URL 可访问性 + title 比对
- 输出篇幅分布、引号问题、缩略语与术语一致性初筛

### 3. 多线程独立 QC

- 优先用 `parallel-vibe`，并把 `.parallel_vibe/` 放到当前 run 内部
- snapshot 只包含最小必要副本：`*.tex/*.bib` + 预检证据包
- 每个 thread 至少覆盖：
  - 文风与可读性
  - 引用真伪与错引风险
  - 篇幅与结构分布
  - 逻辑与论证闭环
  - 缩略语规范
  - 术语一致性
  - 至少 2 类其它 QC

### 4. 汇总聚合

- 主线程合并 threads 的 `RESULT.md`
- 去重、冲突处理、按 `P0/P1/P2` 排序
- 输出最小可执行修改路线

### 5. 标准化报告

最终报告必须包含：

1. 执行摘要
2. 范围与只读声明
3. 硬性问题（P0）
4. 重要建议（P1）
5. 可选优化（P2）
6. 引用核查清单
7. 篇幅与结构分布
8. 建议的最小修改路线图
9. 附录：复现信息

## 常用脚本

```bash
# 一键运行
python3 skills/nsfc-qc/scripts/nsfc_qc_run.py \
  --project-root projects/NSFC_Young \
  --main-tex main.tex \
  --deliver-dir projects/NSFC_Young/QC/vYYYYMMDDHHMMSS \
  --threads 5 \
  --execution serial

# 预检
python3 skills/nsfc-qc/scripts/nsfc_qc_precheck.py --project-root projects/NSFC_Young --main-tex main.tex --out <artifacts_dir> --resolve-refs

# 并行 QC
python3 skills/nsfc-qc/scripts/run_parallel_qc.py --project-root projects/NSFC_Young --run-id vYYYYMMDDHHMMSS --threads 5 --execution serial

# 物化 final 输出
python3 skills/nsfc-qc/scripts/materialize_final_outputs.py --project-root projects/NSFC_Young --run-id vYYYYMMDDHHMMSS
```

## 降级策略

- 若 `parallel-vibe` 不可用，仍需完成同一套 QC 清单。
- 仍要输出标准化报告与 JSON。
- 在附录中说明未启用并行的原因。

## 非目标

- `nsfc-qc` 不是编译检查工具。
- PDF 能否编译成功属于环境/工程质量，不是本技能的核心交付。
