# UCAS-Dissertation

国科大硕士/博士学位论文LaTeX模板, 以《中国科学院大学研究生学位论文撰写规范指导意见》(校发学位字[2022]40号, 附件1) 作为撰写要求

## 项目来源与当前适配范围

本项目最初来源于上游开源仓库 [`LeoJhonSong/UCAS-Dissertation`](https://github.com/LeoJhonSong/UCAS-Dissertation/tree/master)，在 ChineseResearchLaTeX 中以独立 thesis 项目形式接入、整理并继续维护。

当前这份 `thesis-ucas-resource-env` 并非对上游仓库的原样镜像，而是在保留原始 UCAS 论文模板主体结构的基础上，额外补入了现阶段公开可获取的官方要求与资环方向排版约束，主要包括：

- 对齐《中国科学院大学研究生学位论文撰写规范指导意见》（校发学位字〔2022〕40号，附件1）
- 参考当前 UCAS 学位论文 Word 模板的版式要求
- 补充资源与环境学位评定分委员会现阶段使用的写作与排版检查口径
- 接入 ChineseResearchLaTeX 的统一 thesis 构建入口、VS Code 工作区与 DOCX 导出链路

## ChineseResearchLaTeX 集成入口

在本仓库内，优先使用统一构建入口而不是直接手写 `latexmk` 命令：

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-ucas-resource-env --tex-file Thesis.tex
python packages/bensz-thesis/scripts/thesis_project_tool.py clean --project-dir projects/thesis-ucas-resource-env --tex-file Thesis.tex
```

如需导出符合资环学科群 Word 模板样式的 `.docx`（源码转换链路）：

```bash
python3 projects/thesis-ucas-resource-env/scripts/export_docx.py \
  --project-dir projects/thesis-ucas-resource-env \
  --reference-doc 中国科学院大学资环学科群研究生学位论文word模板.docx \
  --output projects/thesis-ucas-resource-env/Thesis_from_tex_资环模板.docx
```

该脚本会同时生成中间文件 `Thesis_from_tex_word_source.md` 和质量报告 `Thesis_from_tex_资环模板_质量报告.md`，用于人工校对与二次修订。
质量报告已接入 `中国科学院大学资源与环境学位评定分委员会研究生学位论文撰写具体要求` 的关键条款自动检查（如 0016/0032/0033/0036/表3/表7），会提示题目长度、摘要字数、关键词数量、页边距、正文与目录标题层级等一致性风险。

如需仅对已生成的 `docx` 重新做样式归一化与质检报告：

```bash
python3 projects/thesis-ucas-resource-env/scripts/export_docx.py \
  --postprocess-only-docx projects/thesis-ucas-resource-env/Thesis_from_tex_资环模板.docx
```

VS Code 场景请直接打开 [`thesis-ucas-resource-env.code-workspace`](./thesis-ucas-resource-env.code-workspace)，
LaTeX Workshop 会通过项目级 `scripts/thesis_build.py` 转调上述统一入口。

## 文件结构

```
.
├── 📁.vscode                      vscode配置文件
├── 📁assets                       图片/附件代码等资产放这里, 如果文件较多建议进一步按章节分为多个文件夹
├── 📁bibs
│   ├── 📒abbreviations.bib        术语表的缩写类术语定义
│   └── 📒mywork.bib               用于“作者简历及攻读学位期间发表的学术论文与其他相关学术成果”章节 (cv.tex) 的个人学术论文及专利的bibtex/biblatex
│   ├── 📒references.bib           参考文献的bibtex/biblatex都放这里
│   └── 📒symbols.bib              术语表的数学符号类术语定义
├── 📦build                        编译出的文件在这个目录, 比如编译出的pdf文件`Thesis.pdf`
├── 📁styles                       本模板核心文件, 定义模板样式
│   ├── 📜ucasDissertation.cls     ucasDissertation文档类定义 (论文样式及附带命令)
│   ├── 📜ucasInfo.sty             提供一组`info.tex`中的论文信息变量设置命令
│   ├── 📜ucasSilence.sty          抑制无用的编译warning
│   └── 📜ucasSpine.cls            书脊样式
├── ⚙️.latexmkrc                   latexmk配置文件, 设置了输出目录, 编译选项, bib2gls及minted的依赖处理规则
├── 📑abstract.tex                 摘要章节
├── 📑acknowledgements.tex         致谢章节
├── 📑appendix1.tex                附录章节, 一章写在一个文件, 根据需要增加
├── 📑chapter1.tex                 正文章节, 一章写在一个文件, 根据需要增加
├── 📑cv.tex                       作者简历章节
├── 🪪info.tex                     论文信息整理于此处
├── 💼spine.tex                    书脊pdf根文件
├── 📕Thesis.pdf                   编译出的论文pdf样例
└── 💼Thesis.tex                   论文pdf根文件
```

项目大致文件结构如上. 论文写作流程:

1. 开始你自己的写作前建议先编译出本模板pdf, 确认输出与[Thesis.pdf](./Thesis.pdf)一致, 以确保你已经配置完善$\LaTeX$写作环境. 另外也建议**参考模板pdf第二章对各类内容的推荐写法**.
2. 在`info.tex`中填写论文信息 (论文标题如果还没想好可以之后再填)
3. 写正文章节, 根据需要在**根目录**增加`chapterN.tex`, 并在`Thesis.tex`中`\include{chapter1}`下方增加一行`\include{chapterN}`. 附录章节操作是类似的.

   > ⚠️ 如果你不是对LaTeX非常熟悉并且已经完全理解本模板, 不建议更改文件结构, 否则可能导致编译失败或部分功能缺失.
   >
   > 比如由于指定了latexmk的`out_dir`为build文件夹, 目前`.latexmkrc`中设置的bib2gls规则仅能正确处理根目录下.tex文件中的`\gls{}`命令.
4. 填写摘要, 致谢, 简历等章节
5. 书脊pdf不需要编辑, 只需要生成
6. 生成查重版pdf：注释`Thesis.tex`中的`\makeCover`, `\makeDeclaration`, 注释插入`abstract.tex`, `acknowledgements.tex`, `cv.tex`的行, 注释显示图表目录和参考文献列表的行,并重新生成
7. 生成盲审版pdf：将`info.tex`中需要隐去的信息都以`-`代替并重新生成即可

## 编译方式

### 在线编辑

⚠️Overleaf免费账户有编译时间限制, 而中国科技云Overleaf似乎在接近毕业节点时负载较大, 会编译很长时间.

将压缩包上传Overleaf或[中国科技云Overleaf](https://www.cstcloud.cn/resources/452) (无编译时间限制) 后在菜单中需将编译器选为`xelatex`. 打开`Thesis.tex`并编译可以生成论文pdf, 打开`spine.tex`并编译可以生成书脊pdf. 由于overleaf/科技云会覆盖`.latexmkrc`中设置的latexmk规则, 输出文件夹被覆写为根目录, 因此想要正常编译**需要做两点修改**:
1. 在行首加`#`, 注释[.latexmkrc](./.latexmkrc)中`$xelatex=`开头的行
   ```diff
   - xelatex = 'xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape -output-directory=%0 %S';
   + #xelatex = 'xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape -output-directory=%0 %S';
   ```
2. 打开 [styles/ucasDissertation.cls](./styles/ucasDissertation.cls)，找到加载 minted 宏包的代码块（`\RequirePackage[...]{minted}`）。如果其中包含 `outputdir=...` 选项，则将其改为 `outputdir=./,`；如果没有该选项，则在选项列表中显式加入一行 `outputdir=./,`
   ```diff
   \RequirePackage[
   +    outputdir=./,
        cachedir=minted_cache,
        newfloat,
   ]{minted}
   ```

### 本地编辑

根目录包含的[.latexmkrc](./.latexmkrc)是**latexmk**的配置文件, 已配置以xelatex为编译器, 运行`latexmk`即可继承该配置进行编译, 生成的pdf文件将在`build`目录下. 运行`latexmk -c`以清理中间文件. 推荐使用安装了**Latex Workshop**插件的**VSCode**进行编辑, [.vscode/settings.json](.vscode/settings.json)中已包含推荐的**Latex Workshop**的配置, [latex-snippets.code-snippets](.vscode/latex-snippets.code-snippets)提供了几个可能用得上的snippet.

#### 依赖安装

- 首先你需要安装一个LaTeX发行版, 推荐安装**TeXLive**.
- 参考文献相关内容使用`biber`生成, Windows平台上这个程序好像一般已经包含在LaTeX发行版中了, 而在Linux下可能需要单独安装[biber](https://github.com/plk/biber)
- 术语表相关内容使用`bib2gls`生成, 这个工具需要借助java, 因此你需要有**java**. 不过术语表 ([这里](https://www.overleaf.com/learn/latex/Nomenclatures)有个简单示例) 仅在文中缩写或符号较多时有一定意义, 不想使用术语表的话, 可以把`Thesis.tex`中`\listofnotations`一行注释掉, 然后删掉章节中调用的所有`\gls{}`命令.
- 代码插入使用`minted`包实现, 其中代码语法高亮依赖于代码语法高亮生成工具[Pygments](https://pygments.org/). 如果你的路径里有Python, 只需`pip install Pygments`即可. (同样如果你不需要插入代码那就不用管)

#### 字体问题

在本地编译时由于操作系统以及系统中已安装的字体的差异, 可能遇到几种问题:

1. 没有模板指定的字体: 本模板指定英文字体为Times New Roman (国科大指导意见要求), 如果你没有, 我建议的解决方案是安装一个[Times New Roman](https://github.com/justrajdeep/fonts/blob/master/Times%20New%20Roman.ttf)

1. ctex自动配置的字体不恰当: 参见[ctex文档](https://tw.mirrors.cicku.me/ctan/language/chinese/ctex/ctex.pdf)4.3节`fontset`选项. `fontset`可作为文档类选项被添加到[Thesis.tex](./Thesis.tex)`\documentclass`的方括号中. **ucasDissertation**文档类基于**ctexbook**文档类实现, 会将所有非[ucasDissertation所定义文档类选项](#文档类选项)的选项传入**ctexbook**文档类

2. 所使用字体不包含特定生僻字, 导致这些生僻字呈现为乱码: 以`xeCJK`包提供的`\CJKfontspec{}`命令临时切换为你指定的系统字体, 在biblatex中同样有效. 比如Fandol的宋体不包含“旸”, 会呈现为乱码, 以`{}`包裹需要临时切换字体的文本, 选一个你系统里安装了的长得像宋体的衬线字体👇

   ```latex
   前面的文字{\CJKfontspec{Noto Serif CJK SC} 旸}后面的文字
   ```

## 文档类选项

**ucasDissertation**文档类提供了几个选项, 可根据需要设置 (取消注释为开启, 注释掉为关闭):

- `print`: 印刷版/电子版 (电子版非另页右页, 仅另页), 关闭时为电子版
- `colorlinks`: 超链接是否彩色, 关闭时为黑色
- `bibBackref`: 是否在参考文献列表中显示文献引用页, 关闭时为不显示
- `draft`: 指定为草稿模式, 会进行简化使生成更快, 在断行不良/溢出出加黑色方块给出提示, 会将pdf压缩等级设为0, 缩短生成时间 (但会导致pdf更大).

## 更多$\LaTeX$帮助

我写了一篇[LaTeX使用笔记](https://leojhonsong.github.io/zh-CN/2021/04/24/LaTeX杂记/), 有兴趣可以看看. 如果仍遇到问题, 欢迎在本仓库提issue.

