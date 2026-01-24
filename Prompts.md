---
ai不要看这个文件，除非用户要求。
---

# Skills 开发


## Skills开发

## 综述skill

我看 /Volumes/2T01/Github/ChineseResearchLaTeX/skills/systematic-literature-review 这个skill改动挺大的，我担心它不能正常工作。 请在 /Volumes/2T01/winE/PythonCloud/Agents/pipelines/reviews/TEST01 里测试/Volumes/2T01/Github/ChineseResearchLaTeX/skills/systematic-literature-review 。如果有bug，就修复。 最后保证/Volumes/2T01/Github/ChineseResearchLaTeX/skills/systematic-literature-review 可以跑通。

## nsfc-justification-writer

请在彻底了解 skills/nsfc-justification-writer 的工作代码/文件后回答： 目前skill的开发度如何？有哪些缺陷？如果有，请指出并将改良计划保存在 plans/v2026010xxxxx.md 里。


## complete_example

```
请你联网调研一下日本演员佐佐木希的发展路程。假设你要以此为题材填写 projects/NSFC_General 。 请使用 skills/complete_example 辅助工作。 最后的排版，PDF要紧凑、美观，大致维持在8页左右。

请你联网调研一下日本演员佐佐木希的发展路程。假设你要以此为题材填写 projects/NSFC_Young 。 请使用 skills/complete_example 辅助工作。 最后的排版，PDF要紧凑、美观，大致维持在8页左右。
```

## make_latex_model

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

## `transfer_old_latex_to_new`

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

