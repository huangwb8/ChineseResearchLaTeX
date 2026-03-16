# 通用

---

创建tag v4.0.1 ； /git-commit ;   /git-publish-release

# 改进

---

Bachelor、Master、Doctor

---

./projects 里的模板的正文里，应该要使用到 enumerate 和 ssssubtitle ，否则用户不知道可以使用它们。

---

模板优化：

- 研究内容样式
- 可否类似fylimas/nsfc那个项目一样列出自己的发表工作

写作skill的优化

- 局限性和本研究的解决方案在逻辑上要统一。
- 立项依据里，科学问题、研究设计、科学假设要统一。
- 方法学细节，不应该在立项依据和研究内容的高层描述中大书特书，只需在研究方法小节里提到即可。
- 类似`在经费与样本质量允许时`这样的表述是绝对禁忌！这类"条件允许时"、"经费允许时"的表述会让评审认为申请人自己都不确信项目可行，是标书写作的大忌。

---

如果本项目要创建新release，要这样做：

- 使用 git-commit skill 创建commit信息并push
- 创建一个新的tag
- 使用 git-publish-release 生成release
- projects里的每个项目，都要生成 .zip 文件，保存在在 ./tests/release-{本次的tag} 这个文件夹里。生成.zip时，zip里仅保留这些文件/文件夹（当然，不能对projects里的文件有任何修改； 这一步只是在一个测试文件夹里生成zip）
  - .vscode
  - bibtex-style
  - code
  - extraTex
  - figures
  - fonts
  - references
  - template
  - main.pdf
  - main.tex
  - README.md
- 把这些zip当作release的Assets推送到github

请把上述规则有机地融入 @AGENTS.md 里

# 重构

---

现在推送至Gitee，都是我手动登陆Gitee然后拉取github里的东西。 能不能搞个自动化流程，当我在github里发布新release的时候，直接把最新的release推送到gitee里？使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。

---

.github/workflows 里的 github action 的自动化流程应该支持最新的字体分离架构。请：

- 完善流程
- 提交release。具体为：
  - 创建tag v4.0.3
  - Git-commit skill 创建commit
  - Git-publish-release skill 创建 release
- 立刻触发1次github action 自动化流程
- 检查项目README里是否已经有cv模板的可下载的zip链接。如果正常就可以结束工作； 否则， 需要反复优化直至成功。

---

Overleaf压缩包你一定要特别关注字体；要保证每个Overleaf包里均有字体（应该不需要全部字体都塞进去； 每个project模板需要的字体是不一样的，有的甚至不需要字体）。总之，要保证Overleaf压缩包可以正常工作。

---

./packages 文件夹里 LaTeX包架构的优化

- latex包有一个很重的资产： 字体。 我希望有一个新的包 ./packages/bensz-fonts 。 它的主要作用是
  - 托管字体文件
  - 提供统一的字体引用的API
  - 作为其它bensz系列latex包的基础包
- 这样设计有几个好处
  - 每个新的latex包开发时，不需要再关注字体怎么引用、设计，因为 bensz-font 已经定义好了这一些
- 注意
  - 目前安装包的时候，bensz-font 包必须是强制安装的（否则，单独安装其它LaTeX包可能无法正常工作）
  - 安装bensz-font 包时，因为它的体积比较大，应该有一个智能选择镜像的功能。 我在 Gitee 里是有镜像的， 中国大陆的用户用Gitee的URL下载应该会快一些，这个请帮忙协调好安装脚本，保证用户可以通过指定某个参数，从而可以在Gitee里下载这个包。其它的包也是类似，都要支持从Gitee镜像里下载。当然，默认还是从Github下载。

这些都是新特性，涉及多项目、多模板，优化难度很大。使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。

---

.github/workflows 里的 github action 的自动化流程应该支持 cv 模板。请：

- 完善流程
- 提交release。具体为：
  - 创建tag v4.0.2
  - Git-commit skill 创建commit
  - Git-publish-release skill 创建 release
- 立刻触发1次github action 自动化流程
- 检查项目README里是否已经有cv模板的可下载的zip链接。如果正常就可以结束工作； 否则， 需要反复优化直至成功。

---

新增简历LaTeX模板支持。 基于/Volumes/2T01/winE/iProjects/Manuscripts/hwbCV （只读） 模仿目前SCI模板的套路，重构形成：

- 包
  - packages/bensz-cv
- 模板
  - projects/cv-01：基于 /Volumes/2T01/winE/iProjects/Manuscripts/hwbCV  的样式。有中/英版。
- 初步验收目标
  - projects/cv-01渲染的PDF和源PDF样式像素级一致（你可以通过将pdf页面转化为jpg，通过视觉智能比较jpg的差别; 要求pdf里每一行的文字、缩进外观都完全一样【这是模板是否优秀的重要标志】）
- 去隐私
  - 完成初步验收目标后，应该去隐私。因为/Volumes/2T01/winE/iProjects/Manuscripts/hwbCV 是真实的简历，正文内容绝不能外传。 你可以构建一些假的内容，作为充分展示模板使用即可。 要求模板支持的所有样式都要用得上。可以使用  projects/NSFC_Young 里提到的佐佐木希。 你可以copy这个头像来用： /Volumes/2T01/winE/我的坚果云/样式备份/头像/zzmx-logo-02.jpg 

这些都是新特性，涉及多项目、多模板，重构难度很大。使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。

---

新增毕业论文模板的支持。基于 /Volumes/2T01/Github/smu-thesis-latex-clinical/projects/mmed-cy-01 和 /Volumes/2T01/winE/iProjects/Manuscripts/thesis_sysu2 , 模仿目前SCI模板的套路，重构形成

- 包
  - packages/bensz-thesis 
- 模板
  - projects/thesis-smu-master：基于  /Volumes/2T01/Github/smu-thesis-latex-clinical/projects/mmed-cy-01 的样式。
  - projects/thesis-sysu-doctor：基于 /Volumes/2T01/winE/iProjects/Manuscripts/thesis_sysu2 的样式。
- 初步验收目标
  - projects/thesis-smu-master和projects/thesis-sysu-doctor渲染的PDF和源PDF样式像素级一致（你可以通过将pdf页面转化为jpg，通过视觉智能比较jpg的差别; 要求pdf里每一行的文字、缩进外观都完全一样【这是模板是否优秀的重要标志】）
- 去隐私
  - 完成初步验收目标后，应该去隐私。因为/Volumes/2T01/Github/smu-thesis-latex-clinical/projects/mmed-cy-01 和 /Volumes/2T01/winE/iProjects/Manuscripts/thesis_sysu2都是真实的毕业论文，正文内容绝不能外传。 你可以构建一些假的内容，作为充分展示模板使用即可。 要求模板支持的所有样式都要用得上。论文主题同 projects/NSFC_Young
  - 论文作者的名字统一为：冯宝宝
- 注意事项：
  - /Volumes/2T01/Github/smu-thesis-latex-clinical/projects/mmed-cy-01的完成度很高，是近期开发的； 因此projects/thesis-smu-master基本上搬过来就能用。  /Volumes/2T01/winE/iProjects/Manuscripts/thesis_sysu2 是很久以前的项目，很多设计肯定不太规范，要好好重构，按projects/thesis-smu-master的架构来重构，应该问题不大
  - 总的来说，它们都是毕业论文模板，很多东西是很像的。这提示packages/bensz-thesis完全可以做得好。 可以参考 packages/bensz-nsfc 是怎么管理公共部分和模板的私有部分的。

这些都是新特性，涉及多项目、多模板，重构难度很大。使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。

---

README文档里的`**## NSFC 公共包安装**`小节改为`**## LATEX包安装**`。写出：

- 可灵活安装包
  - 默认是安装 https://github.com/huangwb8/ChineseResearchLaTeX/tree/main/packages 里有的包
  - 用户可以指定其中的1个或多个包安装。 

- 安装方式
  - 远程硬编码：大致是
    - 用户配置好python环境
    - 运行一个python命令。脚本是https地址，不要是本地地址。
  - 远程ai自主规划：
    - 在Claude Code/Codex里提出Prompt安装（要包含本项目的https链接，这样ai就会自动联网去了解怎么安装）
- 如果目前的架构不支持上述安装方式，可以优化 ./scripts 里的脚本以实现这个目标
- 必要时， AGENTS.md 的内容可以协调、同步优化。

---

Readme文档里的`## 📋 模板列表`进行重构。不再需要我手动地写。 你在本项目开发一个github action流程（你可以看看 /Volumes/2T01/Github/huangwb8/.github/workflows 差不多是这种东西），它的作用是：

- 定期检测最新的release（第1小时检查1次； 用户可以手动触发）
- 在Readme文档里的`## 📋 模板列表`下构建一个格式化的表格，类似于现在的格式； 但里面的信息的实时更新的
- NSFC模板、SCI论文模板、毕业论文模板应该有一定的分隔，样式优雅即可
- Overleaf 演示不放实际的Overleaf地址； 而是放Overleaf包的地址

使用 awesome-code skill 辅助规划、优化。所有要求都要落实。 

---

创建tag v4.0.0，然后发布release。 验收目标：

- 成功release
- Release assets 是正常的，即所有的 projects 里的模板都有普通版zip和overleaf版zip

如果有问题，使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 

---

你理解错了。 我是指， projects/paper-sci-01 的参考文献的docs样式和/Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper 的参考文献的docs样式似乎不完全一样。 问题出在哪？

---

projects/paper-sci-01 的参考文献的docs/pdf的样式和/Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper 似乎不完全一样。 问题出在哪？

---

将 /Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper 是一个已经做好的sci论文写作模板。 现在，请将它移植到本项目，作为一个子功能/子project而存在。 大致如下：

- /Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper/texmf/tex/latex/benszmanuscriptlatex 到这里后变成 packages/bensz-paper
- 基于它添加一个project，保存在 projects/paper-sci-01 代表是适合写sci论文的一个模板
- 你不可以使用  /Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper 里的正文内容，因为那是我未发表的论文。 你可以使用 https://www.cell.com/cancer-cell/fulltext/S1535-6108(26)00110-8 作为模板正文。

注意：

- 不能动nsfc项目
- 因为多了一类项目——SCI写作模板； 也许，其它必要的部分也要调整，比如项目的 AGENTS.md; ./scripts 里的脚本等。 这个你自己把握。

使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。 

验收目标：projects/paper-sci-01里可以渲染出格式标准的PDF和docx。

---

在 projects/NSFC_*/extraTex/@config.tex 里，应该添加大量注释类代码，让用户可以根据自己的需求定制化标书的格式。 我希望

- 所有可调的参数都要列出来； 然后写的是目前的默认值
- 要有说明教用户
  - 这个参数是什么？
  - 应该怎么设置？
- 必须保证 projects/NSFC_*/extraTex/@config.tex 里的参数设置会压过默认的模板设置。在代码逻辑上要保证这一点。

使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。

---

projects/NSFC_General/code/nsfc_build.py 之类的脚本用来干啥的？

---

scripts/pack_release.py 优化：

- 里面除了可以对项目进行一般的打包，还需要打包一个专门可在overleaf中使用的zip。因为，overleaf中用户无法像本地电脑那样随时将一个latex包安装到它的系统里。你只要优化些规则，应该就可以做到。
- 发布版本的时候，压缩包的命名类似于：
  - 普通的可在个人电脑里用的包： NSFC_Young-{release号}.zip
  - 定制的可在Overleaf上使用的包： NSFC_Young-Overleaf-{release号}.zip

使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。

---

对于`用户安装 bensz-nsfc 包后，项目里有稳定办法找到这些脚本`这个需求，解决方法很简单

- 做好安装用的python脚本，让用户不管在什么系统、什么设备里，基于这个python脚本都可以将bensz-nsfc 包安装到正确的位置
- 设计好AGENTS.md的规则，要求ai去latex包的根目录里找脚本。这样ai在实际工作的时候就会自主规划了
- 因为包已经按常规安装正确，一般来说ai肯定很容易找到它（因为latex包一般都装在一些固定的位置）

---

bensz-nsfc/scripts 不需要专门被用户下载； 因为它作为latex包的一部分。 用户只要安装latex包，就可以调用这些脚本了。 你觉得呢？因为，我觉得打包具体项目的zip时，不需要专门把bensz-nsfc/scripts打包进去。

---

请为 ./projects 里的项目添加写标书专用的 AGENTS.md 和 CLAUDE.md 文件，让ai可能更好地辅助用户写标书。 这是很重要的，因为用户一般是下载整个项目文件夹（比如 projects/NSFC_General） 的压缩包； 如果里面已经内置了这2个文件，它就不需要重新使用了。注意，不要动根目录的AGENTS.md 和 CLAUDE.md 文件（它们的主要作用不是写标书，而是开发本项目）。使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。

---

./scripts中和nsfc直接相关的，应该搬到 packages/bensz-nsfc/scripts 里去。AGENTS.md 也要相应地调整、优化。 使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。

---

请了解下 /Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper 是怎么渲染tex为PDF的。 它有这个特点：

- 有固定的python代码负责渲染
- 经过代码渲染后，main.tex目录是很干净的，没有中间文件
- main.pdf和main.tex之前存在跳转连接，在vscode里使用很方便

目前，本项目也许没有达到这种完美的渲染体验。 使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。要保证最终成品能正常、稳定、高效地工作。注意：

- 不需要渲染docx的功能

---

每个项目里 fonts  bibtex-style 是文件体积的大头，3个项目里也是高度一致的。 让这些资源直接托管在  packages/bensz-nsfc 的 assets 文件夹里。 使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。要保证最终成品能正常、稳定、高效地工作。主要考核目标： 项目重构完后，NSFC_General、NSFC_Local、NSFC_Young渲染出来的PDF在外观上和之前完全一样（你可以通过将pdf页面转化为jpg，通过视觉智能比较jpg的差别; 要求pdf里每一行的文字、缩进外观都完全一样【这是模板是否优秀的重要标志】）

---

根据 plans/重构-v202603101512.md 重构本项目。测试用目录在 ./tests/重构-v202603101512 。 我已经做好github备份，你放心大胆地做。使用 awesome-code skill 辅助规划、优化。所有问题都要解决，所有建议都要落实。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。要保证最终成品能正常、稳定、高效地工作。主要考核目标： 项目重构完后，NSFC_General、NSFC_Local、NSFC_Young渲染出来的PDF在外观上和之前完全一样（你可以通过将pdf页面转化为jpg，通过视觉智能比较jpg的差别; 要求pdf里每一行的文字、缩进外观都完全一样【这是模板是否优秀的重要标志】）。

---

其实，我希望核心的latex包也可以随意切换版本。 我的想法是：

- 用户必须通过我定义的python脚本来安装包
- 当用户有安装历史版本的需求时，因为本项目是在github上托管的，因此，只需要请求某个git版本，就可以为用户安装一个旧的版本； 或者，也可以随时进步到任意更新的版本

请优化目前的重构计划。

---

在重构项目的时候，我对一个功能特别需要：模板的版本控制。这是一个巨大的需求：用户在某个时间段，也许不喜欢最新的模板（由于种种原因）。因此，它可能会停留在某个过去的模板很长时间； 但是随时有跟进/回退到模板的任意版本的可能性。因此，我需要项目应该在版本控制这一块做得非常好。请优化目前的重构计划。

---

这里写一下： 

- 我准备对本项目的国自然基金模板进行重构，为未来50年发展打好基础
- 我会新增类似 /Volumes/2T01/winE/iProjects/Manuscripts/CCS/paper 的期刊论文写作latex能力，助力大家使用vibe coding的能力来写论文
- 我会新增类似 /Volumes/2T01/Github/smu-thesis-latex-clinical/projects/mmed-cy-01 的毕业论文写作latex能力，助力毕业的小伙伴使用vibe coding的能力来写论文 

通过上面3个点，让ChineseResearchLaTeX项目变成一个真正的国人latex平台，而不仅限于国自然（尽管国自然仍是重头戏）。要求在400-500字左右。

---

plans/重构-v202603101512.md 的计划觉得可以吗？有没有可以优化的空间？

# 预算说明书

---

创建一个skill，叫 nsfc-budget 。 源代码/工作文件保存在 skills/nsfc-budget 。开发的skill要符合这个规范： https://github.com/huangwb8/skills/blob/main/AGENTS.md 。 该skill的工作流程大致如下：

- 输入：
  - 工作目录： 用户会指定。 如果用户没有指定，你必要暂停工作，要求用户指定一个工作目录。
  - 用户的标书正文； 或者是其它用户指定的材料
  - 总预算：用户提供。 如果用户不提供，就按这个标准： 面上基金50w，地区基金50w，青年基金30w
  - 正文总字数（不包含latex模板文字/代码）：用户提供。如果用户不提供，以800-1000字为宜。一般来说
    - 每个部分不超过500字。
- 工作目录
  - 所有中间文件都保存在工作目录的 .nsfc-budget 隐藏文件夹里
  - 不可以在 .nsfc-budget 隐藏文件夹 以外的地方放任何工作中产生的非结果性的中间文件，免得污染用户的工作目录或其它目录
- 选择latex模板：
  - 默认是 skills/nsfc-budget/models/01 
  - 后续我会放更多模板； 但暂时就1个。 你设计的时候，要为多模板可选做准备
- 彻底理解用户标书的内容，综合latex模板里的预算的要求写标书的预算。
  - 这是一个调研报告，对于如何写预算说明书很有启发，你学习一下 ： /Volumes/2T01/winE/PythonCloud/Agents/pipelines/deep_research_plus/reports/国自然面上基金预算说明书撰写规范 
  - 学习完后将相关策略融入到你开发的skill里
  - 不能硬引用这个目录，因为 /Volumes/2T01/winE/PythonCloud/Agents/pipelines/deep_research_plus/reports/国自然面上基金预算说明书撰写规范 只是一个临时目录，我之后会删除
- 要有理有据、详略得当、逻辑严密，要写出真需求，不要捏造需求。
- 其它你觉得有必要完善的点
- 输出
  - 实际预算说明书的latex项目文件
  - 渲染出budget.pdf
- 目标：一份完美的预算说明书，人类评审专家不可能从中找到任何逻辑漏洞，从而心甘情愿地把基金批给用户。

---

有待改进：

- 设备费、业务费、劳务费 这几个字不要加粗； `请按照《国家自然科学基金项目申请书预算编制说明》等有关要求，按照政策相符性、目标相关性和经济合理性原则，实事求是编制项目预算。填报时，每个科目应结合科研任务按支出用途进行基本测算说明。` 这句话加粗
- 所有的行的断句，请严格执行：

```
1.科学基金资助项目直接费用
请按照《国家自然科学基金项目申请书预算编制说明》等有关要求，按照政策相符性、目标相关性和经济合
理性原则，实事求是编制项目预算。填报时，每个科目应结合科研任务按支出用途进行基本测算说明。
1.1 设备费（是指在项目实施过程中购置或试制专用仪器设备，对现有仪器设备进行升级改造，以及租赁外单
位仪器设备而发生的费用。计算类仪器设备和软件工具可在设备费科目列支。填报时，应按照设备购置费、试制改
造费和租赁使用费的分类，提供设备支出的必要性及基本测算说明。单价大于50万元（含50万元）的设备需补充说
明设备的主要性能指标、主要技术参数等内容。）
1.2 业务费（是指项目实施过程中消耗的各种材料、辅助材料等低值易耗品的采购、运输、装卸、整理等费用，
发生的测试化验加工、燃料动力、出版/文献/信息传播/知识产权事务、会议/差旅/国际合作交流等费用，以及其他
相关支出。填报时，应按照支出大类进行基本测算说明。）
1.3 劳务费（是指在项目实施过程中支付给参与项目研究的研究生、博士后、访问学者以及项目聘用的研究人
员、科研辅助人员等的劳务性费用，以及支付给临时聘请的咨询专家的费用等。填报时，应综合考量劳务费支出对
象所承担研究任务的必要性、投入本项目的工作时长、费用标准的合理性等因素，按照人员类别进行基本测算说明。
专家咨询费应按照国家有关规定执行。）
2.直接费用中合作研究转拨资金
需对合作研究单位承担的研究任务做必要说明。直接费用转拨资金需经项目申请人与参与者协商一致，并按设
备费、业务费、劳务费三个科目做预算说明。如存在多个合作研究单位，请分单位逐一说明。
3.其他来源资金
对其他来源资金的资金来源、资金具体开支用途做简要说明。
```

- 每一行的前面都要缩进2个中文占位

---

有待改进：

- 每一段的前面都要缩进2个中文占位
- 框要更粗点
- 预算说明书和框之间的间隙要小2/3
- 设备费、业务费、劳务费 这几个字要加粗； `请按照《国家自然科学基金项目申请书预算编制说明》等有关要求，按照政策相符性、目标相关性和经济合理性原则，实事求是编制项目预算。填报时，每个科目应结合科研任务按支出用途进行基本测算说明。` 这句话不能加粗
- 每一行的字的数量应该是一样的，但目前不一样。 比如，原版是 `1.1 设备费（是指在项目实施过程中购置或试制专用仪器设备，对现有仪器设备进行升级改造，以及租赁外单`； 但新版是`1.1 设备费（是指在项目实施过程中购置或试制专用仪器设备，对现有仪器设备进行升级改造，以及租赁外单位仪`

---

请仿照 projects/NSFC_Young 的基本框架（只读），基于 projects/Budget_Justification/template/国家自然科学基金项目项目预算说明书（除重大项目、国家重大科研仪器研制项目以外）.docx , 用 [$make_latex_model](/Users/bensz/.codex/skills/make_latex_model/SKILL.md) 制作latex模板

# 摘要skill

---

nsfc-abstract优化

- 写摘要时，研究背景的篇幅小点； 前期研究、拟研究的内容可以稍多点。 研究背景写太多在大多数人类专家眼里是不专业的，因为他们希望看到正在进入正题。

---

nsfc-abstract优化

- 研究领域是一句话； 不能超过25 个汉字；要精简
- 中文摘要里的双引号只能用`“我们”`这样的，不能用其它形式。到时用户是直接copy摘要到系统里面的，上面只支持纯文本，不支持任何其它样式

---

根据/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/materials/标书写作技巧.md 里关于摘要的写作技巧，开发一个名为 `nsfc-abstract` 的skill，保存在 ./skills/nsfc-abstract。 它的作用是： 根据用户提供的内容写标书的中文、英文摘要。 一般有以下要求：
- 要提供中文、英文两个版本。 英文是中文的翻译版
- 中文摘要400字以内（含标点符号）、英文摘要4000字符以内（含标点符号）
- 遵守 /Volumes/2T01/winE/PythonCloud/Agents/pipelines/skills/AGENTS.md 的开发规范
先开发一个demo,然后使用 auto-test-skill 优化1次； 其中的p0-p2级的问题全部都要落实

# 综述skill

- 根据 skills/systematic-literature-review/plans/文献-优化-v202601251638.md 优化skill；如果某些点你有更好的策略，你直接按你的想法就行，不用问我。然后，使用 auto-test-skill 优化1轮。 最后，该skill版本升级为 1.0.9。

- 根据 skills/systematic-literature-review/plans/样式-v202601242025.md 优化skill；如果某些点你有更好的策略，你直接按你的想法就行，不用问我。然后，使用 auto-test-skill 优化1轮。 注意，不要大改 systematic-literature-review 的框架，它目前的业务逻辑很好； 把本次计划里关键的优化点落实就行。最后，该skill版本升级为 1.0.3。不要修改 README.md关于该skill的用法。

- 我看 /Volumes/2T01/Github/ChineseResearchLaTeX/skills/systematic-literature-review 这个skill改动挺大的，我担心它不能正常工作。 请在 /Volumes/2T01/winE/PythonCloud/Agents/pipelines/reviews/TEST01 里测试/Volumes/2T01/Github/ChineseResearchLaTeX/skills/systematic-literature-review 。如果有bug，就修复。 最后保证/Volumes/2T01/Github/ChineseResearchLaTeX/skills/systematic-literature-review 可以跑通。

# VSCode配置

目前， projects 里项目的 .vscode/settings.json 里， xelatex 之类的路径是绝对路径； 或者说是一个确定性的路径。 然而，用户的配置环境可能是很多样的。 不一定是这个路径。 在这方面，有没有办法让 settings.json  变得更加通用，即可以智能识别用户当前环境下的这些编译器的路径？

# nsfc-length-aligner

skills/nsfc-length-aligner 优化

- 目前， 该skill工作时的中间文件可能会泄露，不是严格在工作目录里的 .nsfc-length-aligner 里。我希望可以严格在 .nsfc-length-aligner 里，不要污染项目

# nsfc-reviewers

nsfc-reviewers skill 优化

- 标书的某些部分好坏还受到项目资助力度的限制。一般来说，青年基金只有30-40w，面上项目只有50-60w。因此，用户在设计研究内容/研究方法时，可能会因为这个基金限制而有所妥协（比如，实验设计只能达成一个比较弱的目标）。 但这并不是缺陷，反而是优点，因为国自然的资助额是有限的；如果你觉得用户的研究内容设计的缺陷和这个资助额度有关，你应该在report里说明受基金所限这里的设计有缺陷。并且提醒用户一个完全的设计是怎么样的（假设资助金额没有限制）

# nsfc-code

---

开发一个skill，名为 nsfc-code，保存在 ./skills/nsfc-code 里。 它的基本任务是： 根据标书的内容提供基金代码的选择。它大致的工作原理是：

- 彻底了解标书的正文内容
- 调研 skills/nsfc-code/references/nsfc_code_recommend.toml ，找到最贴切的代码
- 给出5个推荐，每个推荐都包含申请代码1、申请代码2。申请代码1是主要代码，申请代码2是次要代码（但也是比较相关的）
- 每个推荐要附带理由
- 结果保存在工作目录的 NSFC-CODE-v{当前的年月日时分}.md 里。如果用户对保存目录或文件名另有约定，按用户的办。
- 全程对标书内容只读，不要修改。
- 全程按 Skill 开发规范：  https://github.com/huangwb8/skills/blob/main/AGENTS.md

为了更好地开发skill，你可以：

- 先使用 better-prompt skill 优化上述提示词
- 利用 awsome-code skill 辅助规划和工作，确定好ai规划和硬编码的部分。
- 做出一个demo
- 使用 auto-test-skill skill 对该 demo 进行1次优化。

# nsfc-schematic

---

nsfc-schematic 的 nano banana 模式 优化

- 因为 nano banana 的图里的文字，有可能会出现扭曲，降低人类可读性。 为了减少这种情况，我希望 skill的prompt里应该加强图片字体的样式约束，以保证字体生成的规范性，就打打印出来的一样，符合标书的严格需求。 你可以联网找一下大家有哪些经验，一般是怎么写的prompt； 然后有机地融入目前的流程里。
- 必要时要更新skill的readme

---

nsfc-schematic 使用 nano banana 模式时，是不是这样：

- 先理解内容，了解用户的标书内容，制定一个计划
- 请求 nano banana api，获得第1版。它是1个png图
- 宿主ai（就是codex或者claude code所在的ai环境； 非 nano banana ）读这个png图，找到它的不足，然后总结优化建议
- 宿主ai规划一个合适的prompt
- 宿主ai调用一个硬编码代码，将prompt + 第1版的png图传回nano banana api； 获得第2版
- 继续优化（如此类推）
- 直到：
  - 达到了用户定义或者系统默认的自优化次数
  - 宿主ai判断当前的图已经足够好，不需要再改（即触发了早停）
- 结束

目前的流程是这样吗？如果不是，有哪些出入？

---

nsfc-schematic 优化

- 新增一个 基于 Nano Banana 模型 制作原理图的模式。 大致的工作流程是
  - 彻底了解用户的需要
  - 构建合适的prompt
  - 查找用户 .env  里的Gemini配置； 如果能正常连接 nano banana 模型就继续工作（这里需要你设计一些脚本，保存在 skills/nsfc-schematic/scripts 即可）； 不然就中止任务让用户正常配置（目前，我在  .env 我放了一个真实可用的Gemini API，它可以用于访问 Nano Banana 模型； 它一定可以跑通）
  - 完美接入目前的自优化步骤（基于 parallel-vibe ），默认也是5
  - 中间文件的管理基本一样
  - 结果出高分辨率的、能在标书里使用的 png 文件就行，因为 Nano Banana 不支持生成svg和pdf
- 目前的 draw.io 模式是默认的； 这个 Nano Banana 的模式必须用户主动提及才会调用。 所以正常情况下， Nsfc-schematic 的工作过程基本同前。
- 开发完成后，使用 auto-test-skill skill 对 nsfc-schematic 进行1次优化。

---

nsfc-schematic 优化

- 目前， nsfc-schematic 开不同的run不断优化图时， 应该像 nstc-roadmap 一样使用 parallel-vibe 的策略。 请你参考nstc-roadmap，优化一下nsfc-schematic 这方面的设计。

---

使用 auto-test-skill 对 nsfc-schematic 进行1次优化。

---

/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2 是  skills/nsfc-schematic 的1个实例，直接出品。目前，我感觉有一些缺陷：

- 用户明明指定了出图的比例； 但是最终的结果没有严格遵守这个比例。 我希望，当用户指定了图的比例，要严格执行。
- /Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2/.nsfc-schematic/runs 里， 我发现只有 2个runs。 这应该是不对的。 默认的5个run应该全部跑完； 当然，用户可以随意
- 我希望，skill目前的自动布局算法（网格排列、画布拟合）、正交路由算法（避障、waypoints） 、启发式评估（几何度量、阈值检查）  等硬编码执行层（确定性操作）全部转为ai自主规划，充分利用ai的智能
- 其它可能存在的问题，你自己找找

请你彻底地调查 skills/nsfc-schematic 的工作文件和工作代码，充分地理解上述实例暴露出来的问题，给出一个该skill的优化计划，保存在： skills/nsfc-schematic/plans/实例辅助优化-v202603011601.md 里

---

PlanName = 实例辅助优化-v202603011216
按 skills/nsfc-schematic/plans/{PlanName}.md 的要求优化skill；所有的问题都要落实。有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-schematic/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2 是  skills/nsfc-schematic 的1个实例，直接出品。目前，我感觉有一些缺陷：

- 字体很小，整体的人类可读性很差； 你要保证人类可读性。可适当参考 nsfc-roadmap
- PDF的输出有问题，应该保证PDF的输出和png、svg一样是正常的。 可适当参考 nsfc-roadmap 
- 整体的设计是比较差的
- 其它可能存在的问题，你自己找找

请你彻底地调查 skills/nsfc-schematic 的工作文件和工作代码，充分地理解上述实例暴露出来的问题，给出一个该skill的优化计划，保存在： skills/nsfc-schematic/plans/实例辅助优化-v202603011216.md 里

---

PlanName = 实例辅助优化-v202603011030.md
按 skills/nsfc-schematic/plans/{PlanName}.md 的要求优化skill；所有的问题都要落实。有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-schematic/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2 是  skills/nsfc-schematic 的1个实例，直接出品。目前，我感觉有一些缺陷：

- 所有的中间文件，应该在工作目录的 .nsfc-schematic 里托管。 具体参考 nsfc-roadmap 的设计
- 应该有自优化的过程。 具体参考 nsfc-roadmap 的设计

请你彻底地调查 skills/nsfc-schematic 的工作文件和工作代码，充分地理解上述实例暴露出来的问题，给出一个该skill的优化计划，保存在： skills/nsfc-schematic/plans/实例辅助优化-v2026xxxx.md 里

---

PlanName = 实例辅助优化-v202602282149.md
按 skills/nsfc-schematic/plans/{PlanName}.md 的要求优化skill；有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-schematic/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2 是 skills/nsfc-schematic 的1个实例，直接出品。目前，我感觉有一些缺陷：

- 不应该有类似`SeqCCS 原理图：秩排序输入 → 双模态 MLM 预训练 → 个体化分型与验证`这样的标题。不能有图的title； 因为title会占用很多空间
- 有些字，比如尺度约束、缺失约束、异质性约束之类的逻辑箭头里的字太小
- 空间利用率不高。理论上，最上/下/左/右的框框边缘应该很接近画布的边缘
- 有些逻辑箭头会挡住框框里的字
- 框框的形态的选择有点随便，并不够和谐、美观
- 其它有待你发现的问题

请你彻底地调查 skills/nsfc-schematic 的工作文件和工作代码，充分地理解上述实例暴露出来的问题，给出一个该skill的优化计划，保存在： skills/nsfc-schematic/plans/实例辅助优化-v2026xxxx.md 里

---

PlanName = 借鉴roadmap-优化-v202602282005
按 skills/nsfc-schematic/plans/{PlanName}.md 的要求优化skill；有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-schematic/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

PlanName = 借鉴roadmap-优化-v202602191311
按 skills/nsfc-schematic/plans/{PlanName}.md 的要求优化skill；有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-schematic/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

# nsfc-roadmap

---

nsfc-roadmap 和 nsfc-schematic 的 nano banana 模式 优化

- 严禁生成的图片里带有图的总标题。 因为放入标书时这个总标题会被删除，所以没有意义。 

---

nsfc-roadmap 和 nsfc-schematic 的 nano banana 模式 优化

- 多轮自优化时，有时候字体会慢慢变形。 是不是每次优化时，关于字体的约束没有加入prompt里？必须保证每一次与 nano banana 的交互prompt中包含字体相关约束； 否则生成的图片的字体可能会扭曲。

---

nsfc-roadmap 和 nsfc-schematic 的 nano banana 模式 优化

- 目前出png的时候，由于是4k级别的，一般是比较大的。 但是，国自然标书对最终的PDF的文件大小是有要求的。 因此，我希望在原来4k png的基础上，转一个体积变小很多，但质量损耗很小（至少在标书的A4纸打印出来后）的png，命名为 xxx_compacted.png

---

nsfc-roadmap 和 nsfc-schematic 的 readme 优化

- 要写明有 draw.io 模式和 nano banana 模板； 要指出它们的优劣
  - draw.io 可出svg矢量图，但调整需要多轮对话、对于使用者的要求较高
  - nano banana 出图质量很高、很快，但需要配置额外的Gemini API，并且只有高清版png,没有矢量图

---

nsfc-roadmap 和 nsfc-schematic 的 nano banana 模式 优化

- 在自优化的过程中，上一轮的图片是不会传到下一轮的 nano banana api 里的； 这会有个很大的问题：**每次生成的风格都不一样，就像开盲盒一样**。这对于写标书这种严肃的写作场景肯定是不合适的。 我希望可以这样优化：
  - 宿主ai在读图的时候，还要做一个判断——当前的样式是否已经足够好了。 
    - 如果足够好，就输出TRUE； 那么之后的优化过程，下一轮优化时都要传入上一轮的图片，保证风格的延续性。
    - 如果还没足够好，就输出FALSE；此时后续的步骤就基本同目前（就是不会将上一轮的图片传到下一轮）
  - 有时候用户可能会想基于某个run或者某个结果继续优化，那么这时显然也是 TRUE 的情况； ai要能自主判断用户的这个意图，保证图片风格的延续性
- 宿主ai还要判断配色质量是否可以； 给 nano banana api 的prompt里最好要包含配色的建议

---

nsfc-roadmap 和 nsfc-schematic 的 nano banana 模式 优化

- 不管画布是什么尺寸，永远都要输出4k分辨率的图片，以满足出版需要

---

nsfc-roadmap 的 nano banana 模式 优化

- 因为 nano banana 的图里的文字，有可能会出现扭曲，降低人类可读性。 为了减少这种情况，我希望 skill的prompt里应该加强图片字体的样式约束，以保证字体生成的规范性，就打打印出来的一样，符合标书的严格需求。 你可以联网找一下大家有哪些经验，一般是怎么写的prompt； 然后有机地融入目前的流程里。
- 必要时要更新skill的readme

---

nsfc-roadmap使用 nano banana 模式时，是不是这样：

- 先理解内容，了解用户的标书内容，制定一个计划
- 请求 nano banana api，获得第1版。它是1个png图
- 宿主ai（就是codex或者claude code所在的ai环境； 非 nano banana ）读这个png图，找到它的不足，然后总结优化建议
- 宿主ai规划一个合适的prompt
- 宿主ai调用一个硬编码代码，将prompt + 第1版的png图传回nano banana api； 获得第2版
- 继续优化（如此类推）
- 直到：
  - 达到了用户定义或者系统默认的自优化次数
  - 宿主ai判断当前的图已经足够好，不需要再改（即触发了早停）
- 结束

目前的流程是这样吗？如果不是，有哪些出入？

---

PlanName = Gemini画图-优化-v202603012236
按 skills/nsfc-roadmap/plans/{PlanName}.md 的要求优化skill，所有缺陷都要修复。 有疑问的地方，你按最优方案决定，不要问我。在skills/nsfc-roadmap/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

Nsfc-roadmap 优化

- 我希望它可以像 nsfc-schematic 一样支持nano banana 模式。 你参考nsfc-schematic 为Nsfc-roadmap 添加这个模式
- 开发完成后，使用 auto-test-skill skill 对 nsfc-schematic 进行1次优化。
- 使用write-skill-readme skill写好readme

---

目前， nsfc-roadmap输出 PDF时可能会存在严重乱码（多页/拼页）。 请按这个思路修复：

- drawio 文件的 pageWidth/pageHeight 与真实画布一致，避免导出时被切成多页
- PDF 导出时强制 --crop，确保单页输出
- 其它保证PDF准确的设置，你也可以修复

---

PlanName =实例辅助优化-v202602281042
按 skills/nsfc-roadmap/plans/{PlanName}.md 的要求优化skill，所有缺陷都要修复。 有疑问的地方，你按最优方案决定，不要问我。在skills/nsfc-roadmap/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

(～￣▽￣)～ 可优化的点：

- references/models 里有一些新的模板； 你应该更新一下 templates.yaml
- 阶段 1：规划 这部分，步骤我建议这样优化：
  - ai调查必要的tex，彻底了解整个标书的情况。仅看标书的研究内容来决定是不明确的； 应该看标书的立项依据和研究内容，这样可能会有更加全面的把握。
  - 结合标书的实际情况，从 `references/models/templates.yaml` 选模板并生成最终版的 `roadmap-plan.md`
  - 根据`roadmap-plan.md`生成`spec.yaml`
- 阶段 2、3和4的目标要相应调整，因为阶段1有重大变化

# nsfc-humanization

---

PlanName =v202602241320
按 skills/nsfc-humanization/plans/{PlanName}.md 的要求优化skill，所有缺陷都要修复。 有疑问的地方，你按最优方案决定，不要问我。在skills/nsfc-humanization/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

你觉得 skills/nsfc-humanization 还有哪些值得优化的点； 哪些缺陷限制了它所能完成的目标？ 请把优化计划写在： skills/nsfc-humanization/plans/v202602241320.md

---

```
# Identity
你是一位资深的 AI Skill 开发工程师，专注于 NSFC 标书写作辅助工具开发。
你熟悉 LaTeX 格式规范、中文学术写作风格，以及如何识别和消除 AI 生成文本的典型特征。

# Instructions

## 任务目标
在 `./skills/nsfc-humanization/` 目录下开发一个完整的 Agent Skill，
用于将 NSFC 标书内容中的"机器味"去除，使其读起来像资深领域专家亲笔撰写。

## 核心约束（硬性规则，不可违反）
- **格式零修改**：不改动任何 LaTeX 命令、环境、宏定义、注释、空行、缩进
- **语义零损失**：核心论点、数据、引用、逻辑结构完全不变
- **只润色文字**：仅修改纯文本内容的措辞、句式、语气

## "机器味"识别清单（需消除）
- 程式化列举：过度使用"首先…其次…最后…"
- 句式高度重复（如每段都以"本研究将…"开头）
- 逻辑连接词堆砌（"因此"、"综上所述"频繁出现）
- 用词平铺直叙，缺乏专业判断语气
- 缺少领域专家对方法局限性的自然点评

## "资深专家"写作风格（需模仿）
- 句式多样，长短句交替，有节奏感
- 专业术语使用自然，不刻意堆砌
- 论述带有主观判断色彩（"值得注意的是…"、"我们认为…"）
- 逻辑过渡自然，不依赖程式化连接词
- 适当体现领域内的隐性共识

## Skill 文件结构
按照项目 `AGENTS.md` 中的 Skill 开发规范创建：
- `SKILL.md`：AI 执行规范（≤500 行，无版本标记）
- `config.yaml`：元信息与版本管理（从 v0.1.0 起步）
- `README.md`：用户使用指南

## 输入/输出规范
- **输入**：NSFC 标书文本片段（纯文本或 LaTeX 混合文本）
- **输出**：润色后文本，格式与原文完全一致，仅文字内容有变化
- **不适用**：非 NSFC 标书内容 / 需要修改格式 / 需要补充新内容

# Examples

<example id="1">
<input>
本研究将采用深度学习方法对数据进行分析。首先，我们将收集数据。
其次，我们将对数据进行预处理。最后，我们将训练模型并评估结果。
</input>
<output>
本研究拟采用深度学习框架对数据展开系统分析。在数据层面，将构建覆盖
多模态场景的高质量数据集，并针对领域特点设计专项预处理流程；在模型
层面，重点探索所选架构在该任务上的适应性，并通过多维指标对性能进行
全面评估。
</output>
</example>

# Context
- Skill 规范参考：  https://github.com/huangwb8/skills/blob/main/AGENTS.md
- 目标用户：正在撰写 NSFC 标书、希望提升文本质量的科研人员
```

---

请使用 better-prompt skill 优化目前这个prompt：

```
开发一个skill，保存在 ./skills/nsfc-humanization 。 它的任务： 不改动任何格式； 只润色内容，将写作里的“机器味”去除，在保持原意的前提下，让标书的内容看上去像是一位资深的、专业的人类专家所写的。 
```

# nsfc-qc

---

PlanName = 英文缩写检查-v202603080812
按 skills/nsfc-qc/plans/{PlanName}.md 的要求优化skill；有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-qc/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

skills/nsfc-qc关于英文缩写的检查策略要优化：

- 应该将标书正文（所有子tex）当作一个整体来判断英文缩写是否首次出现、英文全称/中文解释是否在全文里唯一
- 应该按实际渲染的顺序，而不是子tex的排名顺序。 因为用户有可能会打乱子tex的渲染顺序。
- 可能还有其它问题，你找找

把优化计划写在： skills/nsfc-qc/plans/英文缩写检查-v202603080812.md

---

目前，nsfc-qc 的逻辑里是否包含术语的规范使用检查？

---

PlanName = 缩写检查-新特性-v202602212344
按 skills/nsfc-qc/plans/{PlanName}.md 的要求优化skill；有疑问的地方，你按最优方案决定，不要问我。在 skills/nsfc-qc/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

(～￣▽￣)～ 根据 skills/nsfc-qc/plans/实例辅助优化-v202602170903.md 优化skill；如果某些点你有更好的策略，你直接按你的想法就行，不用问我。然后，使用 auto-test-skill 优化1轮。

---


(～￣▽￣)～ 这是一个实例： /Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/QC/v202602170654。 有一些问题：

- .nsfc-qc 隐藏文件夹保存在 /Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/.nsfc-qc 而不是 /Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/QC/v202602170654.nsfc-qc。 说明目前skill的文件夹的管理有问题（当前我已经手动纠正； 但我希望以后工作时不要出现类似的错误）
- 你评估一下输出结果，看看还有哪些skill可以改良的空间

将优化计划写到： skills/nsfc-qc/plans/实例辅助优化-v202602170903.md

---

(～￣▽￣)～ 请开发一个skill，保存在 ./skills/nsfc-qc 文件夹里。 它的主要作用是： 对标书进行质量控制。它的步骤大致如下：

- 分析产生的所有中间文件托管在工作目录的 .nsfc-qc 隐藏文件夹里；
- 利用 parallel-vibe skill 开多个thread（默认5个；默认串联模式）独立地进行QC。
- 每个QC做的事情是一样的，大致是：
  - 检查标书里生硬的、不像人类专家写作风格的部分，予以优化
  - 检查每个引用（一般是参考文献）是否存在假引（虚构的引用）、错引（引用的文献和实际的内容不对应）或者其它问题
  - 标书总篇幅是否过长或过短。青年基金和面上基金明确规定：申请书正文原则上不超过30 页，鼓励简洁表达。当然，这是一个推荐性的优化，不是强制的；毕竟写长一点应该问题不大； 但如果太短则不好。
  - 标书不同章节的内容的篇幅分布是否合理
  - 标书不同章节的内容是否逻辑通畅、条理清晰、论证充分、较少歧义
  - 中文为主的标书里， 双引号不能这样用：`"免疫景观"`，而要这样用：```免疫景观"`。
  - 其它你觉得可以做的QC
- 综合所有thread的结果，给出最终优化建议。
- 有标准的输出结果。
- nsfc-qc 对标书内容是只读的，工作过程中不能修改标书的内容。因为它的qc report还需要被进一步审核。

# nsfc-research-content-writer

PlanName = v202602221258
按 skills/nsfc-research-content-writer/plans/{PlanName}.md 的要求优化skill。 使用 awesome-code skill 辅助规划、优化。 有疑问的地方，按你认为最优方案执行，不要问我。在 skills/nsfc-research-content-writer/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

# nsfc-justification-writer

> 最后出品的时候，应该做一些基本的检查； 有没有概念冗余、单调重复出现；要保证整洁、精练、逻辑通畅、行云流水。

---

PlanName = 第三方约束-优化-v202602221613
按 skills/nsfc-justification-writer/plans/{PlanName}.md 的要求优化skill。 使用 awesome-code skill 辅助规划、优化。 有疑问的地方，按你认为最优方案执行，不要问我。在 skills/nsfc-rjustification-writer/tests/{PlanName} 这个文件夹里运行轻量测试以保证项目流程可以正常运行；所有测试时产生的中间文件都必须保存在测试目录里；测试目录必须包含测试的规划文档和报告文档。

---

请在彻底了解 skills/nsfc-justification-writer 的工作代码/文件后回答： 目前skill的开发度如何？有哪些缺陷？如果有，请指出并将改良计划保存在 plans/v2026010xxxxx.md 里。

# nsfc-ref-alignment

---

检验参考文献时，仅检验正文tex里有的参考文献就行； 其它bib里的文献不用管。 目前是这样吗？

---

开发一个名为 nsfc-ref-alignment 的skill，保存在 ./skills 它的作用是： 检查标书里的引用有没有问题。是要保证：

- skill工作时的所有中间文件都托管在工作目录的 .nsfc-ref-alignment 隐藏文件夹里。 每次分析都是 run_xxx 的命名； 后面的 xxx 是时间戳； 这样可以保证每次分析不冲突
- skill工作的时候不修改任务标书的配置或正文，以保证标书内容的安全； 除非用户另有指定。
- 标书里所有的参考文献都是真实存在的，没有错误
- 参考文献的引用与它对应的正文内容是相适应的，不是乱来的
- skill仅输出参考文献的相关报告让用户审核，不直接修改。 因为改标书的参考文献是件大事，要让用户审查一下计划。这个报告默认保存在 ./references 里，除非用户另有指定
- 重点参考 check-review-alignment的开发经验；这是一个类似的skill

先把demo做出来，然后使用 auto-test-skill skill进行1次优化迭代。最后， 使用 write-skill-readme  skill 来写它的README.md； 使用 which-model 来写README的相关章节

# complete_example

```
请你联网调研一下日本演员佐佐木希的发展路程。假设你要以此为题材填写 projects/NSFC_General 。 请使用 skills/complete_example 辅助工作。 最后的排版，PDF要紧凑、美观，大致维持在8页左右。

请你联网调研一下日本演员佐佐木希的发展路程。假设你要以此为题材填写 projects/NSFC_Young 。 请使用 skills/complete_example 辅助工作。 最后的排版，PDF要紧凑、美观，大致维持在8页左右。
```

# make_latex_model

- 正式交付项目

```
使用 `skills/make_latex_model` 这个skill对 projects/NSFC_General 进行改造，使得它的latex系统与 `projects/NSFC_General/template/2026年最新word模板-1.面上项目-正文.doc` 这个最新word模板对齐。

使用 `skills/make_latex_model` 这个skill对 projects/NSFC_Young 进行改造，使得它的latex系统与 `projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.pdf` 这个最新模板对齐。
```

- 测试用脚本

```
请按步骤进行
- 在 skills/make_latex_model/tests/Auto-Test-01 生成一个测试，评估 `make_latex_model`这个skill（下称`目标skill`）的能力。 以 projects/NSFC_Young 为例，利用 projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc 对 projects/NSFC_Young 进行改造（当然，不要直接改动 projects/NSFC_Young 里的原始文件 ；所有过程都在测试目录里进行）。利用 auto-test-skill 这个skill（已经安装在Claude Code/Codex里）进行自动化测试。每一轮测试完成后，目标skill都要变得更好；同时，把Auto-Test-01里上一轮测试的文件清空，在同一个测试目录里进行下一轮测试。如此循环，利用ai的智能不断地优化目标skill。直到目标skill完全正常工作或者超过10轮测试为止。
```

# `transfer_old_latex_to_new`

- 干活

```
请基于`transfer_old_latex_to_new`这个skill把/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026 这个旧项目迁移到/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026_TEST01 这个文件夹里；新项目的模板是 ./projects/NSFC_Young。 注意，千万不能修改或者删除 /Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026 里面的任何文件（完全只读）； 只需要在 NSFC_Young_2026_TEST01 里按要求生成内容就行。 如果你工作时有测试文件/中间文件要生成，请一律放在 ./tests/v202601081624里；测试/中间文件必须要保存在该测试目录里，不要到处“拉屎“。
```

- 测试

```
请按 @plans/v202601081355.md  优化 skill。 允许你在 ./tests/v202601081527 里运行轻量测试以保证交付的skill的质量。测试/中间文件一定要保存在该测试目录里，不要到处“拉屎“。
```

- 原始

```
我希望设计一个skill，名为`transfer_old_latex_to_new`。它的角色是：充当一个具有顶级科研思维的顶尖科学家，将一个旧的研究基金申请书的内容有机地迁移到新的模板中。工作逻辑大致如下：

-输入： 
  - 类似 projects/NSFC_Young 这样的标准latex项目（有main.tex、extraTex、extraTex/@config.tex等成分），它代表的是旧的标书项目，我称为p1
  - 类似类似 projects/NSFC_Young 这样的标准latex项目（有main.tex、extraTex、extraTex/@config.tex等成分），但它是一个已经被调好的新模板，代表的是最新的格式；我称为p2

- 输出： 优化p2

我希望这个skill的大致流程是这样的：
- 识别旧项目的主要部分
- 识别新项目的主要部分
- 比对这些部分的联系和区别，ai自主规划从旧项目迁移到新项目。因为旧项目和新项目在结构上可能大不一样，因此必须依赖ai的智能，不可能存在任何硬编码可以完成这个任务
- 迁移的过程要严格遵守新项目的模板，不能改动模板，只能动内容（一般是extraTex里非 `@config.tex` 的那些文件）
- 完成迁移
- ai再次查看旧项目和新项目。如果觉得新项目写得不好，可以优化。本轮可以重复，但最多不超过5轮（这个5可以硬编码，用户的Prompt可以影响这个参数）。
- 确定新项目比较满意
- latex渲染成pdf。
- 结束

skill开发的时候要遵守 '/Users/bensz/Nutstore Files/PythonCloud/Agents/pipelines/skills' 的相关规范。

请结合 plans/v202601051859.md，给出skill开发计划让我审核。
```


# Legacy

- 请按 plans/v202601051748.md  这个计划设计skill，保存在当前项目的 skills 文件夹内。

- NSFC基金每年的模板都可能会变化。以NSFC_Young为例，一般projects/NSFC_Young/template 里会包含今年的最新模板（比如今年是2026年，那么 projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc 就是最新的官方模板）。而 projects/NSFC_Young/main.tex 有可能是旧的（比如是去年的仿Word样式的Latex模板）。我希望在 `skills` 目录下开发一个skill，名为`make_latex_model`。它的作用是： 在充分了解目前main.tex和projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc的基础上，优化main.tex及其相关的 projects/NSFC_Young/extraTex/@config.tex 文件，以实现对doc的高仿（渲染的PDF和Word版打印的PDF在标题样式上完全一样）。 国自然基金委对格式的要求很严格，因此这种模仿的保真度要求非常高。这个skill在工作的时候要非常注意：1、尽量轻量地修改main.tex和@config.tex，不要进行大的重构（除非有必要这样做），特别是样式的规定。老样式经过长期维护，可靠性非常高；一般只需要在它的基础上优化就行 2、 最新版的word模板有时有main.tex很不一样，有时差不多。你要注意优化时的度，不能过度开发，也不能太懒开发。 3、 skill的开发必须遵守 '/Users/bensz/Nutstore Files/PythonCloud/Agents/pipelines/skills' 的相关规范。请给出开发该skill的计划供我审查。 
