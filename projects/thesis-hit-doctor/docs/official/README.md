# HIT 官方资料记录

本目录用于记录 `thesis-hit-doctor` 的官方资料来源、下载说明与完整性校验值。

## 来源

- 官方页面：<https://hitgs.hit.edu.cn/2021/0513/c17461a318415/page.htm>
- 页面标题：博士研究生学位论文书写范例（理工类）
- 官方附件：<https://hitgs.hit.edu.cn/_upload/article/files/14/4c/be30574d4e4eb9b39160abc5efb5/e0b15208-9a71-4e51-b4a1-0c27d12920ef.doc>
- issue #45 附件：<https://github.com/user-attachments/files/28487527/e0b15208-9a71-4e51-b4a1-0c27d12920ef.1.doc>

## 完整性

2026-06-02 校验时，官方页面附件与 issue 附件内容一致：

```text
6d3ea0a66c6f4145a1adeeccaa4aac330eec95dec2349deab9d038243eca7790  e0b15208-9a71-4e51-b4a1-0c27d12920ef.doc
```

## 分发约定

本项目不直接分发官方 Word 原件。需要做像素级比对时，请从上述官方页面下载附件，并在本地测试目录中转换为 PDF 后使用 `thesis_project_tool.py compare`。
