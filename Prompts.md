

# 通用

---

./projects 里的模板的正文里，应该要使用到 enumerate 和 ssssubtitle ，否则用户不知道可以使用它们。

---

模板优化：

- 研究内容样式
- ~~对于 \begin{enumerate} 里，我希望换行后的首行可以空2个中文字符，这样看上去更加规整。~~
- ~~加粗相关的 AutoFakeBold=3 改为 AutoFakeBold=5~~

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

# 摘要skill

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

/Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2 是  skills/nsfc-schematic 的1个实例，直接出品。目前，我感觉有一些缺陷：

- 用户明明指定了出图的比例； 但是最终的结果没有严格遵守这个比例。 我希望，当用户指定了图的比例，要严格执行。
- /Volumes/2T01/winE/iProjects/Manuscripts/NSFC_Young_2026/roadmaps/SeqCCS原理图-v2/.nsfc-schematic/runs 里， 我发现只有 2个runs。 这应该是不对的。 要默认是5个runs； 并且要跑完。 
- 其它可能存在的问题，你自己找找

请你彻底地调查 skills/nsfc-schematic 的工作文件和工作代码，充分地理解上述实例暴露出来的问题，给出一个该skill的优化计划，保存在： skills/nsfc-schematic/plans/实例辅助优化-v202603011216.md 里

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
