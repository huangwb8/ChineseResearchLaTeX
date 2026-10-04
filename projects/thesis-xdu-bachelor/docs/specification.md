# 西安电子科技大学本科模板依据

## 来源

| 来源 | 性质与使用方式 |
| --- | --- |
| [issue #54](https://github.com/huangwb8/ChineseResearchLaTeX/issues/54) | 要求本科、机电工程学院、机械工程专业，决定项目类型和默认信息 |
| [XDUTS 手册](https://github.com/user-attachments/files/32790331/xduts.pdf) | 6.2.7.2（2025-04-26），涵盖本科与研究生，选择 `xduugthesis` 本科实现 |
| [2025.01 修订 Word](https://github.com/user-attachments/files/32790418/2015.-2025.01.docx) | 研究生学位论文撰写要求，不覆盖本科版式 |
| [摘要要求](https://github.com/user-attachments/files/32790421/default.doc) | 研究生详细摘要要求，不作为本科摘要格式或字数要求 |
| [XDUTS v6.2.7.2](https://github.com/note286/xduts/tree/v6.2.7.2) | 对应手册的公开实现，固定到包内，避免本机旧版改变结果 |

固定上游 commit：`564c3430ddcd83fb475f34c09d225a9dfd04f304`。原始 `xduts.dtx`、`xduts.ins`、README、LPPL 许可证与校徽保存在 `packages/bensz-thesis/styles/xdu/`。本科类通过 `xetex xduts.ins` 提取，未修改上游实现；中文源码必须用 Unicode 引擎提取。校徽版权属于西安电子科技大学。

## 实施范围

- 本科封面含班级、学号、校名、校徽、题目、学院、专业、学生与导师。
- 自动装配中英文摘要、关键词和目录；前置页码为小写罗马数字，正文从阿拉伯数字 1 开始。
- 默认双面、章节右页起始、非对称页边距；本科正文基线为上 3 cm、下 2 cm、内侧 3 cm 加装订偏移 1 cm、外侧 2 cm，封面使用独立参数。
- 正文小四宋体，英文 Times New Roman；章标题黑体三号、居中、段前 24 pt、段后 18 pt。图表、公式、引用和附录编号沿用本科基线。
- 后置材料依次为致谢、参考文献、附录。参考文献标题沿用章标题格式，书目五号；按 issue 指定采用 GB/T 7714—2005 顺序编码制。
- 字体通过共享包文件加载，使本地与 Overleaf 使用相同字形。

## 未提供的本科资料

issue 未附学院专用本科工作手册或最新本科 Word 样稿。当前交付为可编译、可编辑的本科基线，不声称已经与学院最新官方本科样稿完成逐页一致性认证。博士 80 篇、硕士 30 篇文献及研究生详细摘要要求均不自动用于本科；不添加未经提供的本科声明或签名页。若学院要求签名声明，应按其本科原文和页面要求接入。
