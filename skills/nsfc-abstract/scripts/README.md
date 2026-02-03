# scripts（nsfc-abstract）

## validate_abstract.py

对 `nsfc-abstract` 的输出做确定性长度校验：
- 解析 `[ZH]...[/ZH]` 与 `[EN]...[/EN]`（或 `# 中文摘要` / `# English Abstract` 标题格式）
- 默认在计数前将连续空白折叠为单个空格（减少换行/多空格导致的意外超限）

### 用法

```bash
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt
python3 skills/nsfc-abstract/scripts/validate_abstract.py path/to/output.txt --strict
cat path/to/output.txt | python3 skills/nsfc-abstract/scripts/validate_abstract.py -
```

### 退出码

- `0`：成功（且在 `--strict` 下未超限）
- `1`：`--strict` 下超限
- `2`：输入格式错误（缺失分段标记）

## write_abstracts_md.py

把输入内容写成工作目录下的 `NSFC-ABSTRACTS.md`（文件名与标题文本以 `config.yaml:output` 为准），并在末尾追加长度自检。

### 用法

```bash
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_output.txt --strict
cat your_output.txt | python3 skills/nsfc-abstract/scripts/write_abstracts_md.py -
```

### 退出码

- `0`：写入成功（且在 `--strict` 下未超限）
- `1`：`--strict` 下超限
- `2`：输入格式错误（无法解析中英文摘要）
