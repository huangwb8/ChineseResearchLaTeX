# bensz-nsfc 设计原理说明

本文不是使用手册，而是解释 `bensz-nsfc` 为什么会被设计成现在这样。它主要回答三个问题：

- 为什么 NSFC 模板不再把三套样式分别塞进 `projects/NSFC_*`
- 为什么当前结构是“公共包 + profile + 薄项目 + 官方脚本入口”
- 遇到一个问题时，应该改公共包、项目正文，还是脚本

如果你只是想尽快开始写标书，优先读 [`docs/nsfc-usage-guide.md`](./nsfc-usage-guide.md)。如果你想理解这套结构背后的取舍，再读本文。

## 它要解决什么问题

旧式模板仓库最容易出现的问题，不是“功能不够多”，而是“同一份逻辑散落在多个地方”：

- `NSFC_General`、`NSFC_Local`、`NSFC_Young` 各自拷贝一套样式、字体和 `bst`
- 一个排版修复需要在三个项目里重复修改
- Release 包、Overleaf 包、本地安装包之间容易出现资源不一致
- 用户只想写正文，却不得不理解大量样式文件和历史兼容逻辑

`bensz-nsfc` 的核心目标，就是把这些共享复杂度收回到一个公共层，让三套项目尽量只保留“内容”和“最薄的一层入口”。

## 一句话概括当前架构

一句话说，`bensz-nsfc` 现在采用的是：

```text
公共包沉淀共享逻辑
profile 描述项目类型差异
薄项目承载正文入口
官方脚本统一安装、构建、校验与打包
```

这意味着：

- 共享样式、共享字体、共享 BibTeX 资源放在 [`packages/bensz-nsfc/`](../packages/bensz-nsfc/)
- 项目差异通过 [`profiles/`](../packages/bensz-nsfc/profiles/) 表达，而不是复制整份模板
- 项目目录只保留 `main.tex`、`extraTex/`、`references/`、`figures/` 这类和写作直接相关的内容
- 安装、构建、校验尽量都走 [`packages/bensz-nsfc/scripts/`](../packages/bensz-nsfc/scripts/)

## 分层模型

### 1. 薄入口：`bensz-nsfc-common.sty`

[`packages/bensz-nsfc/bensz-nsfc-common.sty`](../packages/bensz-nsfc/bensz-nsfc-common.sty) 几乎不做业务判断，只负责把控制权交给 core。这样做的目的，是让用户项目里始终只记住一个稳定入口：

```latex
\usepackage[type=young]{bensz-nsfc-common}
```

入口越薄，后续内部重构越不容易影响用户项目。

### 2. 核心调度层：`bensz-nsfc-core.sty`

[`packages/bensz-nsfc/bensz-nsfc-core.sty`](../packages/bensz-nsfc/bensz-nsfc-core.sty) 是运行时中枢，主要负责：

- 解析 `type=general|local|young`
- 读取 `bensz-nsfc-runtime.def`，解析公共包根目录与资源路径
- 决定字体和 `bst` 是走公共包资产，还是走项目级兼容兜底
- 载入对应 profile
- 按固定顺序执行项目覆盖钩子
- 分发到 `impl/bensz-nsfc-*.tex`

也就是说，core 关心的是“如何装配”，不是“具体排版细节长什么样”。

### 3. 差异层：`profiles/*.def`

[`packages/bensz-nsfc/profiles/bensz-nsfc-profile-young.def`](../packages/bensz-nsfc/profiles/bensz-nsfc-profile-young.def) 这类 profile 文件只负责描述模板类型差异，例如：

- 模板 ID 与模板版本
- 页边距
- 标题前后间距
- 是否启用 `\frenchspacing`
- 是否启用图题配置、URL 样式等布尔开关

为什么要单独拆出 profile？

- 因为“面上 / 地区 / 青年”的差异本质上是参数差异，不应该演变成三份独立实现
- 把差异收敛成 profile，后续新增模板类型时，优先新增 profile，而不是复制整套样式

### 4. 稳定实现层：`impl/*.tex`

[`packages/bensz-nsfc/impl/bensz-nsfc-young.tex`](../packages/bensz-nsfc/impl/bensz-nsfc-young.tex) 这类文件承载当前已经稳定、可运行、经过回归验证的排版实现。

这里有一个很重要的取舍：项目没有为了“看起来更模块化”就把所有实现强行拆碎。当前仓库保留了 [`bensz-nsfc-layout.sty`](../packages/bensz-nsfc/bensz-nsfc-layout.sty)、[`bensz-nsfc-typography.sty`](../packages/bensz-nsfc/bensz-nsfc-typography.sty) 等骨架文件，但运行时仍优先使用 `impl/` 下的稳定实现。

这体现的是一个偏保守的工程原则：

- 先把稳定实现收口
- 再逐步抽象
- 不为了“未来也许会用到”的结构牺牲当前可维护性

## 项目为什么要保持“薄”

以 [`projects/NSFC_Young/extraTex/@config.tex`](../projects/NSFC_Young/extraTex/@config.tex) 为例，项目层的职责是：

- 给用户一个最直接的可调参数入口
- 保留正文、图片、参考文献等写作资产
- 在不修改公共包的前提下，允许项目级微调

项目层不应该承担的职责是：

- 复制公共字体
- 复制共享 `bst`
- 再维护一套和公共包平行的样式实现

这样设计的直接收益是：普通用户只需要知道“去 `extraTex/*.tex` 写内容”，而不是先理解整套样式源码。

## 加载链路为什么这样安排

从用户项目视角看，典型链路是：

```text
main.tex
-> extraTex/@config.tex
-> \usepackage[type=young]{bensz-nsfc-common}
-> bensz-nsfc-core.sty
-> profiles/bensz-nsfc-profile-young.def
-> impl/bensz-nsfc-young.tex
-> 项目级 after hook 重放关键配置
```

这样做有两个关键原因。

第一，入口稳定。用户长期只需要记住 `@config.tex` 这一个项目入口。

第二，覆盖顺序稳定。公共包默认值、历史兼容接口和项目级覆盖之间必须有确定顺序，否则同一个参数今天能改、明天失效，维护体验会很差。

## 为什么强调“覆盖顺序”

`bensz-nsfc-core.sty` 里已经把覆盖顺序写死了：

1. profile 默认值
2. 兼容旧接口的 `\NSFCBeforePackages` / `\NSFCAfterPackages` / `\NSFCUserOverride`
3. 项目入口专用的 `\NSFCProjectConfigBeforePackage` / `\NSFCProjectConfigAfterPackage`

这套顺序解决的是两个现实问题。

### 问题一：用户需要在项目里改参数，但不想 fork 公共包

于是项目层可以把可调项集中写在 `@config.tex`，由项目级 hook 保证覆盖生效。

### 问题二：仓库里还有历史接口需要兼容

于是旧钩子没有被粗暴移除，而是被放在新机制前面，既保兼容，又让新项目入口拥有更高优先级。

简单说，当前设计追求的是：

- 老项目尽量不断
- 新项目有明确、可预期的覆盖行为

## 资源为什么集中到 `assets/`

[`packages/bensz-nsfc/assets/fonts/`](../packages/bensz-nsfc/assets/fonts/) 和 [`packages/bensz-nsfc/assets/bibtex-style/`](../packages/bensz-nsfc/assets/bibtex-style/) 集中维护共享资源，原因很直接：

- 三套模板本来就在复用同一批字体和 `bst`
- 资源放在项目里会导致重复分发
- 资源更新时容易漏改

同时，core 仍保留了项目级兼容兜底：

- 如果公共包内有字体和 `bst`，优先走公共包
- 如果用户历史项目里仍保留 `./fonts/` 或 `bibtex-style/`，可以临时兜底

这不是鼓励继续分散资源，而是为了平滑迁移旧项目。

## 为什么要有安装器和锁文件

`bensz-nsfc` 不是简单把 `.sty` 复制进项目目录，而是优先安装到 `TEXMFHOME`。对应入口是 [`packages/bensz-nsfc/scripts/install.py`](../packages/bensz-nsfc/scripts/install.py)。

这背后的设计诉求有三条：

- 让多个 NSFC 项目共享同一套公共包，而不是各带一份副本
- 支持按 Git `tag / branch / commit` 安装，方便回到某个稳定版本
- 让项目通过 `.nsfc-version` 记录版本锁，降低“今天能编、明天失真”的风险

因此安装器不仅仅是“复制文件”，它还承担：

- 缓存远端快照
- 写入运行时路径定义
- 记录当前激活状态
- 支持 `pin / sync / check / rollback`

换句话说，安装器服务的不是“首次安装”这一瞬间，而是整个版本生命周期。

## 为什么构建和校验都走官方脚本

当前推荐构建入口是 [`packages/bensz-nsfc/scripts/nsfc_project_tool.py`](../packages/bensz-nsfc/scripts/nsfc_project_tool.py)，而不是让用户长期手写一串裸 `xelatex` 命令。原因主要有三点：

- 它把 `xelatex -> bibtex -> xelatex -> xelatex` 固化成统一链路
- 它会把中间文件尽量收进 `.latex-cache/`
- 它让完整仓库模式和单项目模式都能围绕同一套行为工作

对应地，[`packages/bensz-nsfc/scripts/validate_package.py`](../packages/bensz-nsfc/scripts/validate_package.py) 负责校验公共包本身，而不是依赖某个具体项目“碰巧能编译”。

这体现的是另一个设计原则：公共能力要有公共验证入口，不能把验证责任全压给项目示例。

## 维护时应该改哪一层

可以用下面这组判断来快速分层。

### 应该改 `packages/bensz-nsfc/` 的情况

- 三套 NSFC 模板都会受到影响
- 涉及共享字体、共享 `bst`、共享宏逻辑
- 涉及安装、构建、校验、打包脚本
- 涉及 profile 默认参数或公共资源路径策略

### 应该改 `projects/NSFC_*` 的情况

- 只是示例正文内容要更新
- 只是某个项目的说明文字、示例图片、示例参考文献要调整
- 只是项目层可调参数说明要更清楚

### 应该优先改文档的情况

- 用户困惑来自“为什么这样设计”，而不是功能错误
- 真实代码行为已存在，但没有被解释清楚
- 工作流已经稳定，只是入口说明不够清晰

## 这套设计刻意不做什么

为了保持结构稳定，`bensz-nsfc` 目前刻意避免几件事：

- 不把共享样式重新复制回每个 `projects/NSFC_*`
- 不在 README 之外再发明一套隐藏构建入口
- 不为了“未来可能的扩展”过早引入多层抽象
- 不要求普通用户理解所有公共包源码后才能写正文

这也是为什么当前仓库会优先选择“先有稳定实现，再逐步抽象”，而不是一开始追求最漂亮的理论分层。

## 可以把它理解成什么

如果把整个 NSFC 体系类比成软件工程里的分层系统，那么：

- `packages/bensz-nsfc/` 像共享运行时和公共库
- `profiles/` 像不同发行版的配置集
- `projects/NSFC_*` 像最薄的一层应用入口
- `scripts/` 像官方运维入口

因此，`bensz-nsfc` 的设计重点并不是“写出最多宏”，而是：

- 让共享逻辑只有一份
- 让项目入口尽可能稳定
- 让版本、资源和构建链路可追踪
- 让普通用户和维护者都知道问题该落在哪一层

## 延伸阅读

- [`docs/nsfc-usage-guide.md`](./nsfc-usage-guide.md)：面向使用者的上手说明
- [`packages/bensz-nsfc/README.md`](../packages/bensz-nsfc/README.md)：包级结构、安装入口与资源策略速览
- [`projects/NSFC_Young/extraTex/@config.tex`](../projects/NSFC_Young/extraTex/@config.tex)：项目级参数入口的真实写法
