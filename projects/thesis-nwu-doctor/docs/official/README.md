# NWU 官方资料记录

本目录用于记录 `thesis-nwu-doctor` 的官方资料来源、下载说明与完整性校验值。

## 来源

- issue #48：<https://github.com/huangwb8/ChineseResearchLaTeX/issues/48>
- issue 附件：《西北大学研究生学位论文规范》（研字〔2019〕7号）：<https://github.com/user-attachments/files/28784924/2019.7.1.pdf>
- 研究生院模板页面：<https://yjs.nwu.edu.cn/info/1078/4101.htm>
- 官方模板 zip：<https://yjs.nwu.edu.cn/__local/2/DB/8E/A9684F0CA087522AC12DF242EB4_E0102E1E_287F7.zip?e=.zip>

## 完整性

2026-06-10 校验时，issue 中两个 PDF 附件内容一致；研究生院模板 zip 可公开下载，并包含 `西北大学研究生学位论文模板.docx`。

```text
86722218fedee3e551104238d6d01dcb63b6fa5d7b139a9ce6c451cd5196207a  2019.7.1.pdf
a420f2fcec664c5f1025c3ed77d74891cabea2bddb1e07ad98e7fe565ccfcef5  nwu-official-template.zip
```

## 分发约定

本项目不直接分发官方 PDF、Word 或 zip 原件。需要做像素级比对时，请从上述来源下载资料，并在本地 `tests/` 子目录中转换为 PDF 后使用 `thesis_project_tool.py compare`。
