# 中国科研常用LaTeX模板集

整理中国科研常用的LaTeX模板，包括国自然科学基金的正文模板（Mac/Win/Overleaf）、毕业论文等。一般建议使用最新的[Release](https://github.com/huangwb8/ChineseResearchLaTeX/releases)。

---

<div align="center">

### 🚧 项目开发状态提示

**本项目正处于火热开发阶段！**

当前代码库为活跃开发中的工作版本，功能和模板正在持续完善中。

**⚠️ 建议所有用户使用正式的 [Release 版本](https://github.com/huangwb8/ChineseResearchLaTeX/releases) 以获得最佳稳定性和完整功能支持。**

如需体验最新特性或参与测试，欢迎关注本仓库的开发进展，但请注意可能存在不稳定因素。

</div>

---

<div align="center">

$$\huge \color{#DE2910} \textbf{已经为2026年国自然准备好!更多炸裂特性即将支持！}$$

</div>

## 免责声明

本项目系我结合其它老师的经验总结而维护的模板，仅供交流使用，并不是官方模板；不排除由于本人知识、能力受限而存在参考文献格式、正文字体格式或其它潜在问题。如果您发现存在任何可疑问题，可以提issue，我一定会处理。如果您对本项目有疑虑，建议慎重使用，本人将无法承担任何责任。感谢您的支持！

## 日志

+ **2025-03-12**： :warning:  :warning:  :warning:  v2.5.0版本重大更新！经大佬提醒，发现面上、地区的“3.正在承担的与本项目相关的科研项目xxx”这一段的结尾少了一个分号，请大家记得加上！之前没有看出来，真的非常抱歉！

  ![mQW1QFdXDq](https://chevereto.hwb0307.com/images/2025/03/12/mQW1QFdXDq.png)

+ **2025-03-01**：v2.4.6版本更新。修复一些小问题，基本不影响正常使用。 大家按需食用即可！
  
  + 优化：修改main.tex中的\kaishu为\templatefont以增强字体兼容性。由于主流系统均包含\kaishu，因此可能是一个无关紧要的更新。
  + 优化：改善subsubsection的序号显示以提升\ref{}命令的使用体验；修改正文模板以演示subsubsection序号显示的最佳实践。
  + 修复：直接使用系统TimesNewRoman也适用于MacOS/Overleaf，故不再建议使用外挂TimesNewRoman。感谢[ZhangDY827](https://github.com/ZhangDY827)的提醒！
  
+ **2025-01-31**：v2.4.3版本更新
  + 优化：改善字体设置从而增强对不同正文字体的兼容性。
  
+ **2025-01-25**：v2.4.2版本更新
  + 修复：面上和地区基金的font文件夹缺失
  + 修复：面上模板的`(建议 8000 字以下)`未进行加粗
  + 优化：改善字体设置从而加强对Overleaf/MacOS平台的兼容
  
+ **2025-01-24**：2024版冻结至[v2.3.5](https://github.com/huangwb8/ChineseResearchLaTeX/releases/tag/v2.3.5)。 :sparkles: :sparkles: :sparkles:更新2025版模板 :sparkles: :sparkles: :sparkles:。具体更新说明详见我的博客文章《[国家自然科学基金的LaTeX模板](https://blognas.hwb0307.com/skill/5762)》。

+ **2024-11-18**： :sparkles: :sparkles: :sparkles:本项目即将支持2025国自然模板、支持Mac/Win/Overleaf等多平台，敬请期待！

## 镜像

+ Github源站：[huangwb8/ChineseResearchLaTeX](https://github.com/huangwb8/ChineseResearchLaTeX)
+ Gitee镜像：[huangwb8/ChineseResearchLaTeX](https://gitee.com/huangwb8/ChineseResearchLaTeX)，方便中国大陆的小伙伴访问。

## 背景

经常用LaTeX进行论文、标书写作；但网上的资源比较零散，且距离实用有相当距离。这里整理了部分我修改过的模板，希望对大家有帮助！

## 使用

> 相关技巧详见我的博客文章《[国家自然科学基金的LaTeX模板](https://blognas.hwb0307.com/skill/5762)》。
>
> 测试平台： Windows/MacOS
>
> LaTex发行版： `TexLive`
>
> 编译顺序： `xelatex -> bibtex -> xelatex -> xelatex`

+ [国家自然科学基金 - 青年科学基金项目（C类；2025版）](https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/NSFC_Young) - [Overleaf Demo](https://www.overleaf.com/read/nyrgqdcnvxwq#85f712)
+ [国家自然科学基金 - 面上项目（2025版）](https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/NSFC_General) - [Overleaf Demo](https://www.overleaf.com/read/fnyyxhfcsypb#cc48ee)
+ [国家自然科学基金 - 地区项目（2025版）](https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/NSFC_Local) - [Overleaf Demo](https://www.overleaf.com/read/rwcdbmwkybcp#20eb09)

## 维护者

+ [@huangwb8](https://blognas.hwb0307.com/lyb)

## 使用许可

本项目采用MIT license。详见[LICENSE](https://github.com/huangwb8/ChineseResearchLaTeX/blob/main/license.txt)。

## TODO

- [x] 有面上项目的模板也可以做一下。估计和青年基本一样。
- [ ] 中山大学博士毕业论文LaTeX模板
- [ ] 各种常见基金标书模板
- [ ] 基金标书 & 学位论文LaTeX模板的一致性框架开发

## 历史

+ **2024-02-26**：应小伙伴要求，新增国自然地区科学基金项目LaTeX模板。
+ **2024-02-18**：
  + 优化正文中文字体选择，这可能影响中文加粗。
  + 增强对旧版本TexLive的兼容性：将`main.tex`中类似`{\input{extraTex/1.1.立项依据.tex}}`的代码改为`\input{extraTex/1.1.立项依据.tex}`，即去除最外层的大括号

## 相关仓库

- [Ruzim/NSFC-application-template-latex](https://github.com/Ruzim/NSFC-application-template-latex)
- [Readon/NSFC-application-template-latex](https://github.com/Readon/NSFC-application-template-latex)
- [MCG-NKU/NSFC-LaTex](https://github.com/MCG-NKU/NSFC-LaTex)
- [fylimas/nsfc: nsfc - 国家自然科学基金项目LaTeX模版(青年+面上)](https://github.com/fylimas/nsfc)：这个项目还在比较活跃地更新。
- iNSFC系列
  - [YimianDai/iNSFC: An awesome LaTeX template for NSFC proposal.](https://github.com/YimianDai/iNSFC)：在 MacTeX 和 Overleaf 上均可编译通过。更新也挺频繁。
  - [KimHe/iNSFC: NSFC LaTeX](https://github.com/KimHe/iNSFC)
