# Changelog

All notable changes to this skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-27

### Changed
- 交付报告与 run 目录命名改为秒级时间戳，并在同秒重复运行时自动追加 `-2/-3/...`，避免覆盖与冲突。
- Bib 发现逻辑改为整文件扫描（支持换行与 `\\addbibresource[...]` 可选参数），回退扫描过滤 `.latex-cache/` 与 `.nsfc-ref-alignment/`。
- `\\nocite{*}` 不再污染 citations.csv 与统计（保留 warning/flag）。
- 输出路径尽量相对化；缺少 `bibtexparser` 的 warning 降噪为仅提示一次。

### Fixed
- DOI 在线核验支持常见 DOI 变体归一化，并调整 OpenAlex 编码策略降低假失败。

## [0.1.0] - 2026-02-27

### Added
- 初版：只读方式抽取 NSFC 标书引用与 BibTeX 清单，生成结构化输入与审核报告（中间产物隔离在 `.nsfc-ref-alignment/run_{timestamp}/`，最终报告默认写入 `./references/`）。
