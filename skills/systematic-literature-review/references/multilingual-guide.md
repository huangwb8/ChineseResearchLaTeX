# 多语言支持指南

> 用于把 `{topic}_review.tex` 翻译到目标语言，并尽量保持 LaTeX 可编译。

## 支持范围

- 仅当用户明确要求目标语言时启用
- 支持：`en`、`zh`、`ja`、`de`、`fr`、`es`

## 硬规则

- 只翻译正文自然语言
- 不改：
  - `\cite{key}`
  - LaTeX 命令结构
  - 数学公式
  - 图表标签与交叉引用
  - `.bib`
- 翻译后覆盖原 `{topic}_review.tex`，并先备份为 `.bak`

## 工作流

1. 识别并校验目标语言
2. 生成翻译提示词
3. 备份原 tex
4. 覆盖写入翻译稿
5. 智能编译与修复
6. 导出 PDF / Word
7. 失败时输出错误报告，并支持恢复

## 常用命令

```bash
# 生成翻译任务
python scripts/multi_language.py --tex-file review.tex --language ja

# 仅编译
python scripts/multi_language.py --tex-file review.tex --bib-file refs.bib --compile-only

# 恢复
python scripts/multi_language.py --tex-file review.tex --restore
```

## 常见可修复错误

- 缺宏包
- 未定义命令
- 字体缺失
- 编码错误
- 普通 LaTeX 语法错误

## 不可修复错误

- 权限错误
- 明显内存/环境级失败

## 失败时保留

- `.bak`
- 错误报告
- 必要的 broken 文件
