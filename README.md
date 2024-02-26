# 中国科研常用LaTeX模板集

整理中国科研常用的LaTeX模板，包括国自然科学基金的正文模板、毕业论文等。

## 日志

+ **2024-02-26**：应小伙伴要求，新增国自然地区科学基金项目LaTeX模板。
+ **2024-02-18**：
  + 优化正文中文字体选择，这可能影响中文加粗。
  + 增强对旧版本TexLive的兼容性：将`main.tex`中类似`{\input{extraTex/1.1.立项依据.tex}}`的代码改为`\input{extraTex/1.1.立项依据.tex}`，即去除最外层的大括号

## 镜像

+ Github源站：[huangwb8/ChineseResearchLaTeX](https://github.com/huangwb8/ChineseResearchLaTeX)
+ Gitee镜像：[huangwb8/ChineseResearchLaTeX](https://gitee.com/huangwb8/ChineseResearchLaTeX)，方便中国大陆的小伙伴访问。

## 背景

经常用LaTeX进行论文、标书写作；但网上的资源比较零散，且距离实用有相当距离。这里整理了部分我修改过的模板，希望对大家有帮助！

## 使用

> 相关技巧详见我的博客文章《[国家自然科学基金的LaTeX模板](https://blognas.hwb0307.com/skill/5762)》。编绎平台： `Windows 10 + TexLive 2022 + XeLaTeX + BibTeX`

+ [国家自然科学基金 - 青年项目（2024版）](https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/NSFC_Young)：与面上模板相比，青年模板在`立项依据与研究内容`、`正在承担的与本项目相关的科研项目情况`、`其他需要说明的情况`的第2/3点的文字略有差别；青年模板的内容宽度要略小面上；青年模板的subsection的缩进量被大量人为地调控过，很不统一，估计与面上模板不是出自同一人之手。
+ [国家自然科学基金 - 面上项目（2024版）](https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/NSFC_General)
+ [国家自然科学基金 - 地区项目（2024版）](https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/NSFC_Local)

## 维护者

+ [@huangwb8](https://blognas.hwb0307.com/lyb)

## 使用许可

本项目采用MIT license。详见[LICENSE](https://github.com/huangwb8/ChineseResearchLaTeX/blob/main/license.txt)。

## TODO

- [x] 有面上项目的模板也可以做一下。估计和青年基本一样。
- [ ] 中山大学博士毕业论文LaTeX模板
- [ ] 各种常见基金标书模板
- [ ] 基金标书 & 学位论文LaTeX模板的一致性框架开发

## 相关仓库

- [Ruzim/NSFC-application-template-latex](https://github.com/Ruzim/NSFC-application-template-latex)
- [Readon/NSFC-application-template-latex](https://github.com/Readon/NSFC-application-template-latex)
- [MCG-NKU/NSFC-LaTex](https://github.com/MCG-NKU/NSFC-LaTex)
- [fylimas/nsfc: nsfc - 国家自然科学基金项目LaTeX模版(青年+面上)](https://github.com/fylimas/nsfc)：这个项目还在比较活跃地更新。
- iNSFC系列
  - [YimianDai/iNSFC: An awesome LaTeX template for NSFC proposal.](https://github.com/YimianDai/iNSFC)：在 MacTeX 和 Overleaf 上均可编译通过。更新也挺频繁。
  - [KimHe/iNSFC: NSFC LaTeX](https://github.com/KimHe/iNSFC)
