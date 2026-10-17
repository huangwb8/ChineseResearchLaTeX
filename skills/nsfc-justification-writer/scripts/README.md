# nsfc-justification-writer 脚本

脚本只负责写入安全链：目标定位、路径白名单、引用 key、字数统计、结构变更检查、备份、diff 和回滚。

主流程只有一个：

1. 宿主 AI 读取材料并生成完整正文提案；
2. 运行 `preview`；
3. 脚本检查并自动写入，或用 `--dry-run` 只读检查。

```bash
python skills/nsfc-justification-writer/scripts/run.py preview \
  --project-root <项目目录> \
  --proposal-file <完整正文提案.tex>
```

辅助命令：

```bash
python skills/nsfc-justification-writer/scripts/run.py diagnose --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py refs --project-root <项目目录>
python skills/nsfc-justification-writer/scripts/run.py wordcount --project-root <项目目录>
```

脚本不判断研究逻辑、术语质量、夸大表述或科学问题是否成立；这些判断由宿主 AI 完成。
