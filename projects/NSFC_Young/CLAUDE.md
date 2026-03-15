# NSFC 青年科学基金项目 - Claude Code 适配

## 核心指令

@./AGENTS.md

---

## Claude Code 特定说明

### 文件引用规范

在 Claude Code 中引用文件时，使用 markdown 链接语法：

- **文件**：`[1.1.立项依据.tex](extraTex/1.1.立项依据.tex)`
- **特定行**：`[1.1.立项依据.tex:42](extraTex/1.1.立项依据.tex#L42)`
- **行范围**：`[1.1.立项依据.tex:10-30](extraTex/1.1.立项依据.tex#L10-L30)`

### 任务管理

- 多章节写作任务使用 TodoWrite 工具跟踪进度
- 完成每个章节后及时标记 completed

### 推荐工作流

1. 用户提出写作需求 → 先用 `Read` 读取对应 `extraTex/*.tex` 了解现有内容
2. 判断是否需要调用专项技能（见 AGENTS.md 技能表）
3. 修改内容文件，保持 LaTeX 格式正确
4. 需要时提示用户重新编译验证 PDF 效果

### 默认语言

始终用**简体中文**与用户交流并撰写标书内容。
