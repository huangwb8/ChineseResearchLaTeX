# 官方参考资料（UCAS 资环）

本目录用于保存 `thesis-ucas-doctor` 的官方资料元数据、下载说明与完整性校验值。

因官方 `.doc/.docx` 原件的公开再分发权限未在仓库内获得明确证明，本仓库不直接提交这些原件。请用户自行从官方来源下载后放入本目录。

## 文件清单

- `SHA256SUMS.txt`  
  用途：对用户自行下载的官方原件做完整性校验，避免误替换。

## 建议下载清单

1. 官方来源页面：
   `https://sdc.ucas.ac.cn/index.php/international-students/degree-information/1306-university-of-chinese-academy-of-sciences-degree-thesis-dissertation-guidelines?fid=MTEzNg%3D%3D&task=down`
2. 从该页面下载以下附件后，放入本目录：
   - 附件 3：`Resources and Environmental Science-template.docx`
     建议本地文件名：`中国科学院大学资环学科群研究生学位论文word模板.docx`
     用途：`export_docx.py` 的参考 Word 模板，也是版式与结构实现基线
   - 附件 4：`Resources and Environmental Science 资源与环境.doc`
     建议本地文件名：`中国科学院大学资源与环境学位评定分委员会研究生学位论文撰写具体要.doc`
     用途：资环分委员会“规范条款”原始依据，仅作人工核对条款与验收口径使用

## 校验方式

下载并重命名后，在仓库根目录运行：

```bash
sha256sum -c projects/thesis-ucas-doctor/docs/official/SHA256SUMS.txt
```

## 使用约定

- 不在项目根目录或其他目录保留副本，避免多处拷贝漂移。
- `projects/thesis-ucas-doctor/scripts/export_docx.py` 默认优先从本目录发现参考 Word 模板；若未放置，请显式传入 `--reference-doc <path>`
- `.doc` 文件不参与自动导出流程，仅用于人工比对与验收留痕
- 若更新官方文件，请同步：
  1. 重算 `SHA256SUMS.txt`
  2. 更新项目 `README.md` 的引用说明
  3. 更新根级 `CHANGELOG.md`

## 最近整理

- 目录规范化日期：2026-03-26
- 整理目的：把“来源页面 + 本地文件名约定 + SHA256 校验”收口到统一目录，降低维护与验收歧义。
