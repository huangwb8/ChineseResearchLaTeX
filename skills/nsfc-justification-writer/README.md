# nsfc-justification-writer

本 Skill 以资深国自然标书撰写者的标准撰写、重构、审查和润色立项依据。写作目标是让评审从正文读懂研究为何值得做、科学问题从何而来、假设为何值得检验。宿主 AI 负责科学判断和成稿，Python 负责确定性检查与安全写入。

## 主流程

直接在支持 Skill 的宿主中提出任务：

```text
请使用 nsfc-justification-writer 重构立项依据。
项目目录：/path/to/project
要求：保留已核验事实、引用和 LaTeX 结构，只修改立项依据正文。
请输出论证结构改进、学术表达改进、科学歧义与证据缺口、作者决策事项，附 unified diff、备份路径和回滚命令。
```

宿主 AI 会：

1. 读取目标正文、研究内容、研究基础和参考文献；
2. 识别新写、重构、审查或润色，简短诊断“必须修复、建议优化、可以保留”，重要问题说明位置、依据和影响；
3. 先梳理“临床需求 → 已有认识 → 研究局限 → 科学问题 → 科学假设”，再按诊断起草或修订。非临床课题从相应的科学或应用需求起笔。合理结构与作者声音予以保留。
4. 交稿前逐段检查证据与推理是否承接，修正论证后再润色。写作任务调用 `preview` 安全写入，审查任务交付诊断与建议。

材料不足时登记缺口。新写主张限于证据支持范围；修订既有主张时，改变因果、机制、对象、范围或核心假设须核对依据和已有授权。“证明”降为“提示”、“导致”改为“相关”也可能改变含义，不能自动当作普通润色。未获相关授权或依据不足时，保留待决段落原文，完成其余可保真修订，给出候选建议及影响，不宣称全文已经定稿。已有明确授权无需再次询问。

### 按任务选择修改幅度

| 任务 | 预期行为 |
| --- | --- |
| 新写 | 从材料建立论证，显式登记缺口。 |
| 重构 | 按需重排、合并段落，说明重要调整的理由。 |
| 审查 | 仅诊断与建议，跳过默认写入的 preview；确需候选 diff 时显式使用 `--dry-run`。 |
| 润色 | 优先局部修改，合理标题与段落可以保留，实质问题单列。 |

四类交付说明保持简短：结构改进说明为什么调整或保留；表达改进概括关键变化；证据缺口说明依据、不确定性和实际核验层次；作者决策事项列选项、影响与采用状态。无问题类别写“未发现”。

## 参考资料

- [分节写法](references/section_writing.md)：修订幅度、论证功能、证据组织和科学含义边界。
- [质量控制](references/quality_control.md)：AI 语义审查与脚本安全检查。
- [写作回归样例](references/regression_examples.md)，通过匿名案例复核主线推进、证据强度、修改幅度与只读审查。

不再提供独立的信息表模板：宿主 AI 直接从项目材料提取研究对象、现有瓶颈、科学问题、假设和切入点。需要整理输入时，参照 [`references/section_writing.md`](references/section_writing.md) 的论证地图。诊断命令只输出文本或 JSON，不生成 HTML 报告。

## 写作原则与范围

- 每段推进一个主要判断。保留支撑核心问题的证据、前提和限定，删压旁支材料与重复论述。关键推理应当清楚可见，语言简洁准确。
- 区分已有证据、合理推论与待验证假设。按证据强度表述结论，用项目能澄清的未知和相对已有工作的实质增量说明研究价值。
- 研究意义从实际需求引出一个总的认识缺口，研究现状交代科学问题的证据来由。段数、标题和篇幅比例按论证需要取舍。
- 先说明已有贡献，区分“已考察但未解决、尚未研究或评价、明确条件下不能解决”；未找到报道不等于首次或空白；
- 支持假设的观察参与假设推导，可行性基础简要衔接研究基础，探索性线索保留强度；区分外部研究和团队成果，无前期结果不虚构基础；
- 科学问题与假设采用“现状缺口 → 核心未知 → 项目切入点 → 可证伪预测”的连续叙述；不把 `R1/R2/R3`、`H1/H2`、模型配置、数据划分和评价协议写成问题或假设主体；
- 研究目标、技术路线、主验证场景、终点、阈值和风险处理属于后续章节；
- 字数只按配置的统计口径报告，不设默认目标或容差；如项目有明确篇幅要求，由用户另行指定；
- 不新增无法在项目 `.bib` 中定位的引用；分别说明 bibkey 存在、文献信息可核验和文献支持具体主张，未读足够内容时标明支持性未核验；
- 段首先写科学判断，合并重复限定，保留所有影响解释的必要条件；多个条件可拆句或分段。只用于审查的信息归入交付说明；
- 方法学课题可围绕可识别性、收敛性质、误差界或泛化条件论证科学贡献，不强套生物机制或仅写性能提升；
- 只修改白名单正文，不修改 `main.tex`、`.cls`、`.sty` 或配置文件。

## Python 入口

AI 生成完整正文提案后运行：

```bash
python skills/nsfc-justification-writer/scripts/run.py preview \
  --project-root <项目目录> \
  --proposal-file <完整正文提案.tex>
```

需要只读检查时加 `--dry-run`。仅审查任务不调用默认 `preview`。脚本负责目标路径、白名单、引用 key、结构命令变化、diff、备份和回滚，不判断研究逻辑或文献是否支持具体主张。

常用辅助命令：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root <项目目录>
```

## 写入与回滚

默认 `preview` 会在写入前备份，并输出实际 diff。查看和回滚：

```bash
python skills/nsfc-justification-writer/scripts/run.py list-runs
python skills/nsfc-justification-writer/scripts/run.py diff \
  --project-root <项目目录> --run-id <run_id>
python skills/nsfc-justification-writer/scripts/run.py rollback \
  --project-root <项目目录> --run-id <run_id> --yes
```

## 定向验证

仓库维护使用 Python 3.11+ 和 PyYAML，隔离样稿验证入口：

```bash
python skills/nsfc-justification-writer/scripts/run.py --no-user-override validate-config
python tests/nsfc-justification-writer/test_revision_safety.py --task-root <已声明的任务目录>
```

语义验收按回归样例分别查看正文和交付说明，不能用配置校验或编译成功代替。安装副本可直接使用上述业务 CLI，不要求包含仓库级测试。

版本号以 [`config.yaml`](config.yaml) 的 `skill_info.version` 为准，执行规范见 [`SKILL.md`](SKILL.md)。
