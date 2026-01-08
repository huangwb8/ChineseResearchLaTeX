# nsfc-justification-writer

用于 NSFC 2026 新模板正文 `（一）立项依据` 的写作/重构：把“价值与必要性、现状不足、科学问题/假说、切入点与贡献”写成一段可直接落到 LaTeX 模板的正文，并保持模板结构不被破坏。

## 推荐用法（Prompt 模板）

### 1）从零生成

```
请使用 nsfc-justification-writer：
目标项目：projects/NSFC_Young
主题：<一句话题目/方向>
信息表：<按 references/info_form.md 提供>
输出：写入 extraTex/1.1.立项依据.tex
```

### 2）基于已有草稿重构

```
请使用 nsfc-justification-writer 重构（强调逻辑闭环与可核验性），不要改 main.tex：
目标项目：<你的项目路径>
现有草稿：<粘贴或指向 extraTex/1.1.立项依据.tex>
补充信息：<按 references/info_form.md 缺啥补啥>
```

## 输出文件

- `extraTex/1.1.立项依据.tex`

