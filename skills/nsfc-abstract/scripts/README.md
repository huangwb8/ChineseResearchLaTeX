# scripts（nsfc-abstract）

## validate_abstract.py

对 `nsfc-abstract` 的输出做确定性约束校验（长度 + 分段完整性 + 严格模式下的中文格式）：
- 解析标题建议分段（`[TITLE]...[/TITLE]` 或 `# 标题建议`）
- 解析 `[ZH]...[/ZH]` 与 `[EN]...[/EN]`（或 `# 中文摘要` / `# English Abstract` 标题格式）
- 解析“主要研究领域”分段（`[FIELD]...[/FIELD]` 或 `# 主要研究领域`）
- 默认在计数前将连续空白折叠为单个空格（减少换行/多空格导致的意外超限）
- `--strict` 下额外检查：中文摘要中不应出现英文双引号 `"`（应改为中文引号 `“...”`）
- `--strict` 下额外检查：中文摘要数字不应使用千分位逗号（如 `1,000` / `1，000`，应改为 `1000`）

### 用法

```bash
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt --strict
cat path/to/output.txt | python3 skills/nsfc-abstract/scripts/validate_abstract.py -

# JSON（机器可读）+ diff（超出字符数）
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt --json --diff

# 向后兼容旧输出（不要求标题分段）
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt --no-title

# 向后兼容旧输出（不要求“主要研究领域”分段）
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt --no-field
```

### 退出码

- `0`：成功（且在 `--strict` 下无约束违规）
- `1`：`--strict` 下存在约束违规（超限/中文标点/数字格式等）
- `2`：输入格式错误或缺失必需分段（如缺 TITLE/FIELD 等）

## write_abstracts_md.py

把输入内容写成工作目录下的 `NSFC-ABSTRACTS.md`（文件名与标题文本以 `config.yaml:output` 为准），并在末尾追加长度自检。

同时支持把标题建议分段写入 `# 标题建议`（标题分段默认是必需项，取决于 `config.yaml:title.title_required`），并写入“主要研究领域”分段 `# 主要研究领域`（是否必需取决于 `config.yaml:field.field_required`）。

额外硬约束（为了避免写出不可提交文件）：
- 中文摘要出现英文双引号 `"` 或数字千分位逗号 `1,000/1，000` 时，**无论是否 `--strict` 均拒绝写入**
- `--out` 仅允许单文件名（不允许 `../` 或 `a/b.md` 这类路径），保证输出留在当前工作目录

### 用法

```bash
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt --strict
cat your_output.txt | python3 skills/nsfc-abstract/scripts/write_abstracts_md.py -

# auto-compress（占位：当前版本不自动压缩，超限则提示并返回 1）
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt --auto-compress

# JSON 报告（stdout 仅打印 JSON；写入路径输出到 stderr）
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt --json
```

### 退出码

- `0`：写入成功（且在 `--strict` 下无长度超限）
- `1`：约束违规导致拒绝写入（例如：`--strict` 下超限，或中文摘要包含 `"` / `1,000`）
- `2`：输入格式错误或非法输出文件名（缺失必要分段、无法解析中英文摘要、`--out` 非单文件名等）
