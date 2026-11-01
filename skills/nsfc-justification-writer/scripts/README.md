# 脚本入口

脚本只处理可重复的确定性工作：目标定位、引用检查、字数统计（不设目标）、结构变更检查、备份、diff、写入和回滚。研究逻辑、章节安排和语言修改由宿主 AI 完成。

## 主流程

1. 宿主 AI 判断任务类型并诊断；写作任务生成完整正文提案，仅审查任务输出诊断与建议，不进入默认写入流程。
2. 运行 `preview` 检查正文 diff。
3. 检查通过后自动写入；需要只读检查候选 diff 时加 `--dry-run`。脚本不判断科学主张变更是否有依据及授权，宿主 AI 须按质量控制先完成语义复核。

```bash
python skills/nsfc-justification-writer/scripts/run.py preview \
  --project-root <项目目录> \
  --proposal-file <完整正文提案.tex>
```

## 辅助命令

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root <项目目录>
```

`core/` 中的模块按职责拆分：`coordinator.py` 负责目标和诊断编排，`security.py` 负责路径白名单，`change_guard.py` 负责正文 diff，`editor.py` 和 `versioning.py` 负责备份、写入和回滚。脚本没有信息表生成入口；输入清单和写作方法见 [`../references/section_writing.md`](../references/section_writing.md)。
