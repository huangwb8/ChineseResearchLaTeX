# nsfc-abstract

用于生成 NSFC 标书的中文摘要与英文摘要（英文为中文的忠实翻译），并做长度约束自检：
- 中文摘要默认 ≤400 字符（含标点）
- 英文摘要默认 ≤4000 字符（含标点）

版本信息见 `skills/nsfc-abstract/config.yaml:skill_info.version`。
长度阈值以 `skills/nsfc-abstract/config.yaml:limits` 为准。
默认输出写入**工作目录**下的 `NSFC-ABSTRACTS.md`（中文/英文各一个 `#` 标题，标题文本见 `config.yaml:output`）。

## 何时使用

当你明确想要：
- “写/润色标书摘要”
- “生成中文摘要 + 英文摘要”
- “把中文摘要翻译成英文摘要（并确保长度合规）”

## 你需要提供什么

推荐按信息表提供：`skills/nsfc-abstract/references/info_form.md`。

最少也请给出：
- 研究对象与重要性（1-2 句）
- 未解决科学问题（1 句）
- 前期发现/预实验（1-2 条）
- 拟验证的假说/核心判断（1 句）
- 研究内容 3-4 点（每点包含：做什么/怎么做/验证什么）
- 预期意义（1 句）

## 推荐 Prompt（可直接复制）

```text
请使用 nsfc-abstract：
我将提供信息表，请你生成中文摘要（≤400字，含标点）以及对应英文摘要（≤4000字符，含标点，且英文为中文的忠实翻译版，不新增信息）。
输出请写入工作目录下的 NSFC-ABSTRACTS.md：
- 中文一个 # 标题
- 英文一个 # 标题
并在文件末尾给出两段的字符数自检。
```

## 长度校验脚本（可选）

如果你已经有包含摘要内容的文件（支持两种格式：`[ZH]/[EN]` 标记，或 `# 中文摘要`/`# English Abstract` 标题），可运行校验：

```bash
python3 skills/nsfc-abstract/scripts/validate_abstract.py NSFC-ABSTRACTS.md --strict
```

脚本会解析 `[ZH]...[/ZH]` 与 `[EN]...[/EN]`，并报告字符数与是否超限。

本 skill 自带一个可运行示例：`skills/nsfc-abstract/examples/demo_output.txt`（可用于验证脚本与输出格式）。

## 写入文件脚本（可选）

如果你拿到了模型输出（例如包含 `[ZH]/[EN]` 标记的文本），想一键写成 `NSFC-ABSTRACTS.md`，可用：

```bash
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt
```

也支持从 stdin 读取：

```bash
cat my_abstract.txt | python3 skills/nsfc-abstract/scripts/validate_abstract.py -
```

### 退出码约定

- `0`：解析成功，且未使用 `--strict` 或（使用 `--strict` 时）未超限
- `1`：使用 `--strict` 且存在超限
- `2`：输入格式错误（例如缺失 `[ZH]/[EN]` 分段标记）
