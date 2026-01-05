---
name: transfer-old-latex-to-new
description: 智能迁移旧版NSFC标书到新版模板：分析旧新项目结构、AI自主规划迁移策略、执行内容迁移、迭代优化、编译验证。用于用户要求"迁移标书/升级模板/跨版本迁移/旧标书转新模板"。
---

# LaTeX 标书智能迁移器

## 0.5) 深度参考版本差异指南（强制）

**执行时机**: 每次迁移开始前的第一阶段

**必须读取的参考文档**:
1. `references/version_differences_2025_2026.md` - 版本结构差异详解
2. `references/structure_mapping_guide.md` - 章节映射决策参考
3. `references/migration_patterns.md` - 常见迁移模式库

**理解要点**:
- 掌握不同版本NSFC模板的结构变化科学政策背景
- 理解章节编号体系变化（数字编号 vs 汉字编号）
- 熟悉常见的一对一、一对多、多对一迁移模式
- 了解哪些章节是新增的、哪些是删除的、哪些是重组的

---

## 0) 前置约束（铁律，每次迁移都要遵守）

### 0.1 修改范围约束

**✅ 只修改以下内容**:
- `extraTex/*.tex` 内容文件（**排除** `@config.tex`）
- 新项目中的 `references/*.bib` 参考文献文件（如需更新引用格式）

**❌ 绝不修改以下内容**:
- `main.tex` 模板结构文件（任何情况下）
- `@config.tex` 配置文件
- 模板中的 `.cls`、`.sty` 样式文件
- 任何影响编译环境的系统文件

### 0.2 流程约束

- **迁移前必须自动备份**原项目（除非用户明确跳过）
- **LaTeX编译必须通过**才算迁移完成（无致命错误）
- **内容完整性优先于格式完美**（先保证内容不丢失，再优化格式）

### 0.3 质量底线

- 旧内容丢失率 = 0%（所有科学内容必须迁移）
- 逻辑断裂点必须人工修复或标记
- 引用错误必须修复（`\ref`、`\cite`）

---

## 1) 触发条件识别

当用户提到以下**关键词**或**意图**时触发本技能：

### 直接触发词
- "迁移标书"、"升级模板"、"跨版本迁移"
- "旧标书转新模板"、"2025转2026"、"2024转2025"
- "项目结构变化"、"内容重组"、"模板升级"

### 隐式触发场景
- 用户提到"我有去年的标书想用今年的模板"
- 用户提到"换了新版本后内容怎么迁移"
- 用户提到"两个版本结构不一样怎么处理"

### 需收集的参数（按需收集）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `old_project_path` | 必填 | 旧项目根目录（绝对路径） |
| `new_project_path` | 必填 | 新项目根目录（绝对路径） |
| `backup_path` | 自动生成 | 备份目录（默认：`../.backup/项目名_时间戳`） |
| `max_rounds` | 5 | 最大优化轮次 |
| `strategy` | "smart" | 迁移策略：smart（智能）/ conservative（保守）/ aggressive（激进） |
| `content_generation` | "smart" | 新增内容生成：smart（调用技能）/ placeholder（占位）/ skip（跳过） |

---

## 2) 标准迁移工作流（六阶段）

### Phase 0: 参数验证与准备

**目标**: 确保输入有效，环境就绪

**步骤**:

#### 0.1 路径验证
```python
# 伪代码逻辑
validate_paths(old_project_path, new_project_path):
    # 检查路径存在性
    assert os.path.exists(old_project_path), "旧项目路径不存在"
    assert os.path.exists(new_project_path), "新项目路径不存在"

    # 检查项目结构标准性
    assert has_main_tex(old_project_path), "旧项目缺少 main.tex"
    assert has_extra_tex_dir(old_project_path), "旧项目缺少 extraTex/"
    assert has_main_tex(new_project_path), "新项目缺少 main.tex"
    assert has_extra_tex_dir(new_project_path), "新项目缺少 extraTex/"

    return True
```

#### 0.2 版本识别
```python
detect_project_version(project_path):
    # 读取 main.tex 文件头
    # 识别特征：
    # - 文档类（ctexart vs nsfcarticle）
    # - 章节编号样式（1.1 vs （一））
    # - 特定注释或标记
    # 返回：版本字符串（如 "2025"、"2026"、"未知"）
```

#### 0.3 创建备份
```python
create_backup(old_project_path, new_project_path):
    # 默认备份到 ../.backup/项目名_YYYYMMDD_HHMMSS/
    # 仅备份用户可编辑的内容：
    # - extraTex/*.tex
    # - references/*.bib
    # - figures/（如有）
    # 不备份：main.tex、.cls、.sty
```

**输出**: 备份路径、版本识别结果

---

### Phase 1: 双向结构深度分析

**目标**: 完全理解旧新项目的结构差异

#### 1.1 旧项目结构分析

**执行**: 使用 `scripts/analyze_structure.py` 或手动解析

**输出**: `sections_map_old.json`

```json
{
  "project_path": "/path/to/Old_NSFC_Young",
  "version": "2025",
  "main_structure": {
    "sections": [
      {
        "level": 1,
        "title": "（一）立项依据与研究内容",
        "number": "1",
        "subsections": [
          {
            "level": 2,
            "title": "1. 项目的立项依据",
            "number": "1.1",
            "content_file": "extraTex/1.1.立项依据.tex",
            "word_count": 1500,
            "has_references": true,
            "label": "sec:rationale"
          }
        ]
      }
    ]
  },
  "extra_files": [
    "extraTex/@config.tex",
    "extraTex/1.1.立项依据.tex",
    "extraTex/1.2.研究内容.tex",
    "extraTex/1.3.研究目标.tex",
    ...
  ],
  "config": {
    "document_class": "ctexart",
    "compiler": "xelatex"
  }
}
```

**关键解析点**:
- 章节树结构（`\section`、`\subsection` 层级）
- 每个章节对应的内容文件（通过 `\input{...}` 或 `\include{...}`）
- 标签定义（`\label{...}`）
- 引用使用（`\ref{...}`、`\cite{...}`）

#### 1.2 新项目结构分析

**同 1.1 流程**，输出 `sections_map_new.json`

#### 1.3 智能差异分析

**执行**: 对比两个 JSON，推断映射关系

**输出**: `structure_diff.json`

```json
{
  "mapping": {
    "one_to_one": [
      {
        "old": "extraTex/1.1.立项依据.tex",
        "new": "extraTex/1.1.项目的立项依据.tex",
        "similarity": 0.95,
        "confidence": "high"
      }
    ],
    "one_to_many": [
      {
        "old": "extraTex/1.3.方案及可行性.tex",
        "new": [
          "extraTex/1.4.研究方案.tex",
          "extraTex/1.5.可行性分析.tex"
        ],
        "reason": "新模板将'方案'与'可行性'拆分为两个独立小节",
        "split_strategy": "semantic_split"  // 按"研究方法"和"可行性分析"语义切分
      }
    ],
    "many_to_one": [
      {
        "old": [
          "extraTex/1.1.立项依据.tex",
          "extraTex/1.2.研究意义.tex"
        ],
        "new": "extraTex/1.1.项目的立项依据.tex",
        "reason": "新模板将'研究意义'合并入'立项依据'",
        "merge_strategy": "sequential_merge"  // 顺序拼接，添加过渡
      }
    ],
    "new_added": [
      {
        "file": "extraTex/1.6.研究风险应对.tex",
        "reason": "新模板明确要求单独列出风险应对措施",
        "content_source": "generate_from_context",  // 基于旧项目内容生成
        "priority": "medium"
      }
    ],
    "removed": [
      {
        "file": "extraTex/3.5.其它.tex",
        "reason": "新模板删除此章节，内容可忽略或迁移到其它章节"
      }
    ]
  },
  "structural_changes": {
    "major": [
      "第一板块从'立项依据与研究内容'拆分为两个独立一级标题",
      "新增'研究基础与工作条件'独立板块（原在'研究内容'中）"
    ],
    "minor": [
      "章节编号从数字（1.1）改为汉字（一）/数字（1.1）混合",
      "参考文献格式要求变化"
    ]
  },
  "risk_assessment": {
    "high_risk": [
      "1.3→1.4+1.5 拆分可能导致内容逻辑断裂",
      "新增'研究风险应对'需要AI生成内容"
    ],
    "medium_risk": [
      "合并章节需要添加过渡段",
      "引用标签需要全局更新"
    ]
  }
}
```

---

### Phase 2: AI自主规划迁移策略

**目标**: 基于结构差异分析，自主决策迁移方案

#### 2.1 AI决策点与自主规划规则

**以下决策点由AI自主完成，无需用户确认**:

| 决策点 | AI输入 | AI自主决策规则 | 输出 |
|--------|--------|----------------|------|
| **迭代轮次** | 项目规模、结构复杂度 | 规则：<br>- 简单一对一迁移：3轮<br>- 中等复杂度：5轮<br>- 高复杂度：7轮<br>- 收敛即提前退出 | `max_rounds: 5` |
| **迁移策略** | 结构差异分析结果 | 规则：<br>- one_to_one ≥ 80%：conservative<br>- one_to_many/many_to_one ≥ 30%：smart<br>- new_added ≥ 3：smart | `strategy: "smart"` |
| **新增内容生成** | 缺失章节、旧项目上下文 | 规则：<br>- 高优先级缺失：调用写作技能<br>- 中优先级：基于上下文生成<br>- 低优先级：占位符 | `content_generation: "smart"` |
| **备份方式** | 项目路径、时间戳 | 规则：<br>- 自动创建快照到 `../.backup/`<br>- 跳过已存在的备份（用户可指定覆盖） | `backup_path: "../.backup/项目名_20260105_192456"` |
| **LaTeX编译失败处理** | 错误类型、严重程度 | 规则：<br>- 缺失文件：中止并报告<br>- 语法错误：尝试自动修复<br>- 引用错误：修复后继续<br>- 超过3次失败：中止并保留日志 | `action: "attempt_fix_then_abort"` |

#### 2.2 生成迁移计划

**输出**: `migration_plan.json`

```json
{
  "metadata": {
    "generated_at": "2026-01-05T19:24:56",
    "ai_model": "claude-opus-4-5",
    "strategy": "smart",
    "estimated_rounds": 5
  },
  "migration_tasks": [
    {
      "id": 1,
      "priority": "high",
      "phase": "content_migration",
      "type": "one_to_one",
      "source": "old/extraTex/2.1.研究基础.tex",
      "target": "new/extraTex/3.1.研究基础.tex",
      "actions": [
        "读取源文件内容",
        "检查LaTeX环境完整性",
        "修复可能的语法错误",
        "写入目标文件"
      ],
      "validation": [
        "文件非空",
        "LaTeX语法有效",
        "字数 ≥ 原文件95%"
      ],
      "risks": [
        "可能需要调整章节层级",
        "引用需要更新"
      ],
      "fallback": "如果迁移失败，保留原文并标记错误"
    },
    {
      "id": 2,
      "priority": "high",
      "phase": "content_migration",
      "type": "one_to_many",
      "source": "old/extraTex/1.3.方案及可行性.tex",
      "targets": [
        "new/extraTex/1.4.研究方案.tex",
        "new/extraTex/1.5.可行性分析.tex"
      ],
      "split_strategy": {
        "method": "semantic_split",
        "cues": [
          "在'研究方案'部分保留：技术路线、实验方法、数据采集",
          "在'可行性分析'部分保留：理论可行性、技术可行性、团队条件"
        ],
        "transition": "在两个文件间添加过渡段，确保逻辑连贯"
      },
      "actions": [
        "读取源文件",
        "按语义边界拆分内容",
        "为每个目标文件生成过渡段",
        "保持LaTeX环境完整性",
        "写入目标文件"
      ],
      "risks": [
        "语义边界可能模糊",
        "需要AI智能判断拆分点",
        "可能需要手动调整"
      ]
    },
    {
      "id": 3,
      "priority": "medium",
      "phase": "content_generation",
      "type": "new_added",
      "target": "new/extraTex/1.6.研究风险应对.tex",
      "generation_strategy": {
        "method": "call_skill",
        "skill": "nsfc-methods-feasibility-writer",
        "context": "从旧项目的'方案及可行性'中提取风险点",
        "prompt_template": "基于以下研究方案，识别潜在技术风险、进度风险，并给出应对措施：{context}"
      },
      "actions": [
        "分析旧项目内容提取风险点",
        "调用写作技能生成风险应对",
        "整合到新文件",
        "验证与整体一致性"
      ],
      "validation": [
        "内容相关性 ≥ 80%",
        "与旧项目内容逻辑一致",
        "符合NSFC写作规范"
      ]
    }
  ],
  "optimization_plan": {
    "rounds": 5,
    "focus_areas": [
      {
        "round": 1,
        "focus": ["逻辑连贯性", "过渡段质量"],
        "tools": ["manual_review", "nsfc-writing-core"]
      },
      {
        "round": 2,
        "focus": ["术语一致性", "引用完整性"],
        "tools": ["grep_terminology", "ref_validator"]
      },
      {
        "round": 3,
        "focus": ["内容深度", "证据充分性"],
        "tools": ["nsfc-rationale-writer", "nsfc-innovation-writer"]
      },
      {
        "round": 4,
        "focus": ["格式规范", "LaTeX编译"],
        "tools": ["latex_compiler", "linter"]
      },
      {
        "round": 5,
        "focus": ["全文通读", "最终润色"],
        "tools": ["nsfc-writing-core"]
      }
    ],
    "convergence_criteria": [
      "LaTeX编译无错误",
      "逻辑连贯性评分 ≥ 4/5",
      "连续2轮无明显改进"
    ]
  },
  "validation_checks": [
    {
      "check": "LaTeX编译通过",
      "severity": "critical",
      "command": "cd new_project && xelatex main.tex"
    },
    {
      "check": "所有章节非空",
      "severity": "warning",
      "test": "word_count > 50 for each section"
    },
    {
      "check": "引用完整性",
      "severity": "warning",
      "test": "no undefined \\ref or \\cite"
    },
    {
      "check": "内容完整性",
      "severity": "critical",
      "test": "旧核心内容100%迁移"
    }
  ]
}
```

---

### Phase 3: 内容智能迁移执行

**目标**: 按照迁移计划，逐任务执行迁移

#### 3.1 一对一迁移（简单映射）

**执行逻辑**:
```python
def one_to_one_migration(task, old_project, new_project):
    """
    简单的一对一迁移
    """
    # 1. 读取源文件
    source_path = Path(old_project) / task['source']
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. 基础LaTeX语法检查
    content = fix_latex_syntax(content)

    # 3. 更新引用标签（如有需要）
    content = update_references(content, task)

    # 4. 写入目标文件
    target_path = Path(new_project) / task['target']
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        'status': 'success',
        'word_count': count_words(content),
        'warnings': []
    }
```

**关键点**:
- 保持 `\section{}`、`\subsection{}` 等结构标记
- 不修改章节标题（由模板控制）
- 只迁移文件内容，不修改模板结构

#### 3.2 一对多/多对一迁移（结构重组）

**一对多（拆分）执行逻辑**:
```python
def one_to_many_migration(task, old_project, new_project):
    """
    将一个文件拆分到多个文件
    """
    source_path = Path(old_project) / task['source']
    with open(source_path, 'r', encoding='utf-8') as f:
        full_content = f.read()

    # AI智能拆分点识别
    split_points = ai_identify_split_points(
        full_content,
        targets=task['targets'],
        strategy=task['split_strategy']
    )

    results = []
    for i, target in enumerate(task['targets']):
        # 提取对应部分
        if i == 0:
            part_content = full_content[:split_points[0]]
        elif i == len(task['targets']) - 1:
            part_content = full_content[split_points[-1]:]
        else:
            part_content = full_content[split_points[i-1]:split_points[i]]

        # 添加过渡段（第一部分除外）
        if i > 0:
            transition = ai_generate_transition(
                previous_part=full_content[split_points[i-2]:split_points[i-1]],
                current_part=part_content,
                context="从旧章节的'{prev_title}'过渡到新章节的'{curr_title}'"
            )
            part_content = transition + "\n\n" + part_content

        # 写入目标文件
        target_path = Path(new_project) / target
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(part_content)

        results.append({
            'target': target,
            'word_count': count_words(part_content)
        })

    return {
        'status': 'success',
        'parts': results
    }
```

**多对一（合并）执行逻辑**:
```python
def many_to_one_migration(task, old_project, new_project):
    """
    将多个文件合并到一个文件
    """
    contents = []
    for source in task['sources']:
        source_path = Path(old_project) / source
        with open(source_path, 'r', encoding='utf-8') as f:
            contents.append(f.read())

    # AI智能合并
    merged_content = ai_merge_contents(
        contents=contents,
        strategy=task.get('merge_strategy', 'sequential_merge'),
        context="合并'{sources}'到新章节'{target}'"
    )

    # 写入目标文件
    target_path = Path(new_project) / task['target']
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(merged_content)

    return {
        'status': 'success',
        'word_count': count_words(merged_content),
        'sources_count': len(contents)
    }
```

#### 3.3 新增内容生成

**执行逻辑**:
```python
def generate_new_content(task, old_project, new_project):
    """
    为新增章节生成内容
    """
    # 从旧项目提取上下文
    context = extract_context_from_old_project(
        old_project,
        relevant_sections=task.get('context_sources', [])
    )

    if task['generation_strategy']['method'] == 'call_skill':
        # 调用其他NSFC写作技能
        skill_name = task['generation_strategy']['skill']
        prompt = task['generation_strategy']['prompt_template'].format(
            context=context
        )

        # 调用技能（通过Skill工具）
        generated_content = invoke_skill(skill_name, prompt)

    elif task['generation_strategy']['method'] == 'generate_from_context':
        # 基于上下文直接生成
        generated_content = ai_generate_content(
            context=context,
            section_title=task['target'],
            requirements=task.get('requirements', [])
        )

    # 写入目标文件
    target_path = Path(new_project) / task['target']
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(generated_content)

    return {
        'status': 'success',
        'generation_method': task['generation_strategy']['method'],
        'word_count': count_words(generated_content)
    }
```

#### 3.4 交叉引用修复

**执行逻辑**:
```python
def fix_cross_references(new_project, ref_mapping):
    """
    修复所有交叉引用
    """
    # 扫描所有 \ref{} 和 \cite{}
    ref_pattern = re.compile(r'\\(ref|cite)\{([^}]+)\}')

    for tex_file in Path(new_project).glob('extraTex/*.tex'):
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换引用
        def replace_ref(match):
            ref_type = match.group(1)
            ref_key = match.group(2)

            if ref_key in ref_mapping:
                return f'\\{ref_type}{{{ref_mapping[ref_key]}}}'
            else:
                # 记录未找到映射的引用
                log_warning(f"Reference '{ref_key}' not found in mapping")
                return match.group(0)

        content = ref_pattern.sub(replace_ref, content)

        # 写回文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(content)
```

---

### Phase 4: 迭代优化循环（最多5轮）

**目标**: 通过多轮优化，提升迁移质量

#### 4.1 优化流程

```python
def iterative_optimization(new_project, plan, max_rounds=5):
    """
    迭代优化，最多5轮
    """
    optimization_report = []

    for round_num in range(1, max_rounds + 1):
        print(f"\n{'='*60}")
        print(f"优化轮次 {round_num}/{max_rounds}")
        print(f"{'='*60}\n")

        # 4.1 质量评估
        quality_score = assess_quality(new_project, plan)

        # 4.2 收敛判断
        if is_converged(quality_score, optimization_report):
            print(f"✅ 质量已达标，提前退出优化（第{round_num}轮）")
            break

        # 4.3 问题诊断
        issues = diagnose_issues(new_project, quality_score)

        # 4.4 优化执行
        improvements = execute_optimizations(
            new_project,
            issues,
            focus_area=plan['optimization_plan']['focus_areas'][round_num-1]
        )

        # 4.5 记录进度
        round_report = {
            'round': round_num,
            'quality_score': quality_score,
            'issues_found': len(issues),
            'improvements_made': improvements,
            'converged': is_converged(quality_score, optimization_report)
        }
        optimization_report.append(round_report)

        # 输出进度
        print_round_report(round_report)

    return optimization_report
```

#### 4.2 质量评估标准

```python
def assess_quality(new_project, plan):
    """
    评估当前迁移质量
    """
    scores = {}

    # 1. LaTeX编译状态
    scores['latex_compilation'] = check_latex_compilation(new_project)

    # 2. 章节完整性
    scores['section_completeness'] = check_section_completeness(new_project, plan)

    # 3. 逻辑连贯性（AI评估）
    scores['logical_coherence'] = ai_evaluate_coherence(new_project)

    # 4. 术语一致性
    scores['terminology_consistency'] = check_terminology_consistency(new_project)

    # 5. 引用完整性
    scores['reference_integrity'] = check_reference_integrity(new_project)

    # 综合评分
    total_score = sum(scores.values()) / len(scores)

    return {
        'total': total_score,
        'breakdown': scores
    }
```

#### 4.3 收敛判断逻辑

```python
def is_converged(current_score, history_reports):
    """
    判断是否收敛
    """
    # 收敛条件（满足任一即提前退出）
    convergence_criteria = [
        current_score['total'] >= 0.9,  # 总分≥90%
        len(history_reports) >= 2 and  # 连续2轮改进<5%
            abs(history_reports[-1]['quality_score']['total'] -
                history_reports[-2]['quality_score']['total']) < 0.05,
        current_score['latex_compilation'] == 1.0 and  # 编译完美且无其他严重问题
            all(s >= 0.8 for s in current_score['breakdown'].values())
    ]

    return any(convergence_criteria)
```

#### 4.4 每轮优化重点

| 轮次 | 优化重点 | 使用工具/技能 | 预期改进 |
|------|----------|---------------|----------|
| **第1轮** | 逻辑连贯性、过渡段质量 | 手动检查 + `nsfc-writing-core` | 消除明显的逻辑断裂 |
| **第2轮** | 术语一致性、引用完整性 | Grep + 引用验证器 | 统一术语，修复引用 |
| **第3轮** | 内容深度、证据充分性 | `nsfc-rationale-writer`、`nsfc-innovation-writer` | 补充证据锚点 |
| **第4轮** | 格式规范、LaTeX编译 | LaTeX编译器 + Linter | 消除编译错误/警告 |
| **第5轮** | 全文通读、最终润色 | `nsfc-writing-core` | 提升可读性 |

---

### Phase 5: 最终验证与交付

**目标**: 确保迁移成功，生成交付物

#### 5.1 LaTeX编译验证

```python
def validate_latex_compilation(new_project):
    """
    完整的LaTeX编译流程
    """
    project_path = Path(new_project)

    # 标准编译流程：xelatex -> bibtex -> xelatex -> xelatex
    commands = [
        f"cd {project_path} && xelatex -interaction=nonstopmode main.tex",
        f"cd {project_path} && bibtex main",
        f"cd {project_path} && xelatex -interaction=nonstopmode main.tex",
        f"cd {project_path} && xelatex -interaction=nonstopmode main.tex"
    ]

    compilation_log = []
    for i, cmd in enumerate(commands, 1):
        print(f"编译步骤 {i}/4: {cmd.split()[-1]}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode != 0:
            compilation_log.append({
                'step': i,
                'status': 'error',
                'output': result.stderr
            })
            return {
                'success': False,
                'failed_at_step': i,
                'log': compilation_log
            }
        else:
            compilation_log.append({
                'step': i,
                'status': 'success',
                'warnings': extract_warnings(result.stdout)
            })

    # 检查PDF是否生成
    pdf_path = project_path / 'main.pdf'
    if not pdf_path.exists():
        return {
            'success': False,
            'reason': 'PDF not generated',
            'log': compilation_log
        }

    return {
        'success': True,
        'pdf_path': str(pdf_path),
        'warnings': sum(step.get('warnings', []) for step in compilation_log),
        'log': compilation_log
    }
```

#### 5.2 结构完整性检查

```python
def validate_structure_completeness(new_project, plan):
    """
    检查所有新模板章节是否有内容
    """
    required_sections = extract_required_sections_from_template(new_project)

    empty_sections = []
    for section in required_sections:
        content_file = section['content_file']
        file_path = Path(new_project) / content_file

        if not file_path.exists():
            empty_sections.append({
                'section': section['title'],
                'issue': 'file_not_exist'
            })
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否为空或仅包含模板占位符
        word_count = count_chinese_words(content)
        if word_count < 50:
            empty_sections.append({
                'section': section['title'],
                'issue': 'insufficient_content',
                'word_count': word_count
            })

    return {
        'all_complete': len(empty_sections) == 0,
        'empty_sections': empty_sections
    }
```

#### 5.3 内容质量终检

```python
def final_quality_check(new_project):
    """
    最后的质量检查
    """
    checks = {}

    # 1. 全文通读（AI）
    checks['readability'] = ai_full_text_review(new_project)

    # 2. 关键科学论点核查
    checks['scientific_arguments'] = verify_key_arguments(new_project)

    # 3. 引用完整性验证
    checks['citations'] = verify_all_citations_valid(new_project)

    # 4. 格式一致性
    checks['formatting'] = check_formatting_consistency(new_project)

    return {
        'passed': all(check['status'] == 'pass' for check in checks.values()),
        'details': checks
    }
```

#### 5.4 生成交付物

```python
def generate_deliverables(new_project, optimization_report, validation_results):
    """
    生成完整的交付物
    """
    deliverables_dir = Path(new_project) / '.migration_deliverables'
    deliverables_dir.mkdir(exist_ok=True)

    # 1. PDF输出
    pdf_path = Path(new_project) / 'main.pdf'
    if pdf_path.exists():
        shutil.copy(pdf_path, deliverables_dir / 'migrated_proposal.pdf')

    # 2. 迁移日志
    migration_log = generate_migration_log(optimization_report)
    with open(deliverables_dir / 'migration_log.md', 'w', encoding='utf-8') as f:
        f.write(migration_log)

    # 3. 变更摘要
    change_summary = generate_change_summary(new_project)
    with open(deliverables_dir / 'change_summary.md', 'w', encoding='utf-8') as f:
        f.write(change_summary)

    # 4. 备份恢复说明
    restore_guide = generate_restore_guide()
    with open(deliverables_dir / 'restore_guide.md', 'w', encoding='utf-8') as f:
        f.write(restore_guide)

    # 5. 结构对比报告
    structure_comparison = generate_structure_comparison(new_project)
    with open(deliverables_dir / 'structure_comparison.md', 'w', encoding='utf-8') as f:
        f.write(structure_comparison)

    return {
        'deliverables_dir': str(deliverables_dir),
        'files': [
            'migrated_proposal.pdf',
            'migration_log.md',
            'change_summary.md',
            'restore_guide.md',
            'structure_comparison.md'
        ]
    }
```

---

## 3) 智能决策指南（AI推理增强点）

### 3.1 章节对应关系推断

**启发式规则**:
1. **标题相似度匹配**: 使用编辑距离算法计算章节标题相似度
2. **编号规则匹配**: 识别编号模式（1.1 vs （一））
3. **内容语义分析**: 读取前100字，判断主题相似性
4. **位置启发式**: 相邻章节更可能对应

**AI推理辅助**:
```
输入：旧章节标题 "1.3 方案及可行性"、新章节标题 "1.4 研究方案" 和 "1.5 可行性分析"

推理过程：
1. 计算标题相似度：
   - "1.3 方案及可行性" vs "1.4 研究方案" = 0.6
   - "1.3 方案及可行性" vs "1.5 可行性分析" = 0.7

2. 分析关键词重叠：
   - 旧标题包含："方案"、"可行性"
   - 新标题分别包含："方案"、"可行性"

3. 结论：一对多关系，需要拆分

输出：{"type": "one_to_many", "confidence": 0.9}
```

### 3.2 内容拆分/合并策略

**拆分策略**:
- **语义边界优先**: 按自然段落和主题边界拆分
- **保留LaTeX环境**: 确保 `\begin{itemize}` 等环境完整
- **添加过渡段**: 在拆分点生成自然衔接

**合并策略**:
- **顺序拼接**: 按源文件顺序合并
- **添加过渡段**: 在合并点生成衔接段落
- **去重处理**: 删除重复的引言或总结

### 3.3 新增内容生成

**决策树**:
```
IF 新章节有明确旧章节对应
    THEN 基于旧章节内容改编
ELSE IF 新章节与多个旧章节相关
    THEN 综合多个旧章节生成
ELSE
    THEN 调用写作技能从零生成
END IF
```

**调用技能示例**:
```python
# 新增"研究风险应对"章节
context = """
从旧项目的以下部分提取风险点：
1. 技术路线中的关键技术难点
2. 可行性分析中的潜在问题
3. 研究基础中可能存在的不足
"""

generated_content = invoke_skill(
    "nsfc-methods-feasibility-writer",
    prompt=f"基于以下研究方案，撰写'研究风险应对'部分：{context}"
)
```

### 3.4 优化评估标准

**量化指标**:
```python
quality_metrics = {
    'logical_coherence': {
        'weight': 0.3,
        'measure': 'AI评分(0-1)',
        'threshold': 0.8
    },
    'content_completeness': {
        'weight': 0.3,
        'measure': '迁移内容字数 / 原内容字数',
        'threshold': 0.95
    },
    'latex_compilation': {
        'weight': 0.2,
        'measure': '编译成功? 1:0',
        'threshold': 1.0
    },
    'reference_integrity': {
        'weight': 0.1,
        'measure': '有效引用数 / 总引用数',
        'threshold': 0.9
    },
    'terminology_consistency': {
        'weight': 0.1,
        'measure': '术语一致性评分',
        'threshold': 0.85
    }
}

total_score = sum(
    metrics[k]['measure'] * metrics[k]['weight']
    for k in quality_metrics
)
```

---

## 4) 工具与脚本接口规范

### 4.1 脚本调用规范

所有辅助脚本位于 `scripts/` 目录，通过以下方式调用：

```bash
# 结构解析
python scripts/analyze_structure.py --project /path/to/project --output structure.json

# 差异分析
python scripts/compare_structures.py --old old_structure.json --new new_structure.json --output diff.json

# LaTeX编译验证
python scripts/validate_latex.py --project /path/to/project --compiler xelatex
```

### 4.2 错误处理流程

```python
def safe_execute(task, fallback_action):
    """
    安全执行任务，失败时执行降级方案
    """
    try:
        result = execute_task(task)
        if result['status'] == 'success':
            return result
        else:
            log_warning(f"Task failed: {result['error']}")
            return fallback_action(task)
    except Exception as e:
        log_error(f"Exception: {str(e)}")
        return fallback_action(task)
```

### 4.3 输出格式要求

所有JSON输出必须符合以下规范：
- 使用UTF-8编码
- 键名使用snake_case
- 数组按优先级排序
- 包含 `generated_at` 时间戳
- 包含 `ai_model` 使用的模型

---

## 5) 质量保证检查表

### 迁移前检查

- [ ] 旧项目路径有效且包含 `main.tex`
- [ ] 新项目路径有效且包含 `main.tex`
- [ ] 两个项目都有 `extraTex/` 目录
- [ ] 已创建项目备份
- [ ] 已读取版本差异指南

### 迁移中检查

- [ ] 结构分析完成（生成 `sections_map_old.json` 和 `sections_map_new.json`）
- [ ] 差异分析完成（生成 `structure_diff.json`）
- [ ] 迁移计划已生成（`migration_plan.json`）
- [ ] 所有迁移任务已执行
- [ ] 交叉引用已修复

### 迁移后检查

- [ ] LaTeX编译通过（无致命错误）
- [ ] 所有章节非空
- [ ] 逻辑连贯性评分 ≥ 4/5
- [ ] 内容完整性 ≥ 95%
- [ ] 引用完整性验证通过
- [ ] 已生成所有交付物

---

## 6) 常见问题与故障排除

### Q1: LaTeX编译失败，提示"Undefined control sequence"

**原因**: 新旧模板宏包不同

**解决方案**:
1. 检查缺失的命令是否来自旧模板特有宏包
2. 在新模板中找到对应命令或宏包
3. 替换为兼容的写法

### Q2: 迁移后章节内容为空

**原因**: 映射关系推断错误

**解决方案**:
1. 检查 `structure_diff.json` 中的映射关系
2. 手动调整映射关系
3. 重新执行迁移

### Q3: 交叉引用全部失效

**原因**: 标签编号变化

**解决方案**:
1. 运行 `fix_cross_references` 脚本
2. 检查 `ref_mapping` 是否完整
3. 手动修复无法自动映射的引用

### Q4: 优化循环不收敛

**原因**: 质量评分标准过于严格或存在无法修复的问题

**解决方案**:
1. 检查优化报告，定位问题点
2. 放宽某些非关键指标阈值
3. 标记无法修复的问题，继续其他优化

---

## 附录A: 快速开始示例

### 示例1: 简单一对一迁移

```
用户: "帮我把去年的标书迁移到今年的新模板"

AI执行流程:
1. 收集参数: old_project_path="/path/to/old", new_project_path="/path/to/new"
2. 执行 Phase 0-5
3. 输出: "迁移完成！编译通过，质量评分 92/100"
4. 交付物: {PDF, 迁移日志, 变更摘要}
```

### 示例2: 复杂结构重组

```
用户: "2025版标书升级到2026版，结构变化挺大的"

AI执行流程:
1. 识别高复杂度迁移
2. 智能规划拆分/合并策略
3. 执行迁移 + 5轮优化
4. 输出: "复杂迁移完成，共拆分3个章节，合并2个章节，新增1个章节"
5. 交付物: {PDF, 迁移日志, 结构对比报告}
```

---

**SKILL.md 版本**: v1.0
**最后更新**: 2026-01-05
**维护者**: AI Agent (Claude Code)
