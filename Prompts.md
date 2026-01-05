---
ai不要看这个文件，除非用户要求。
---

- NSFC基金每年的模板都可能会变化。以NSFC_Young为例，一般projects/NSFC_Young/template 里会包含今年的最新模板（比如今年是2026年，那么 projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc 就是最新的官方模板）。而 projects/NSFC_Young/main.tex 有可能是旧的（比如是去年的仿Word样式的Latex模板）。我希望在 `skills` 目录下开发一个skill，名为`make_latex_model`。它的作用是： 在充分了解目前main.tex和projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc的基础上，优化main.tex及其相关的 projects/NSFC_Young/extraTex/@config.tex 文件，以实现对doc的高仿（渲染的PDF和Word版打印的PDF在标题样式上完全一样）。 国自然基金委对格式的要求很严格，因此这种模仿的保真度要求非常高。这个skill在工作的时候要非常注意：1、尽量轻量地修改main.tex和@config.tex，不要进行大的重构（除非有必要这样做），特别是样式的规定。老样式经过长期维护，可靠性非常高；一般只需要在它的基础上优化就行 2、 最新版的word模板有时有main.tex很不一样，有时差不多。你要注意优化时的度，不能过度开发，也不能太懒开发。 3、 skill的开发必须遵守 '/Users/bensz/Nutstore Files/PythonCloud/Agents/pipelines/skills' 的相关规范。请给出开发该skill的计划供我审查。 

