# `bensz-fonts` 如何支持其它包

`bensz-fonts` 不是一个“单纯存放字体文件的目录”，而是 `ChineseResearchLaTeX` 里专门负责共享字体资产与字体调用 API 的基础包。它为 `bensz-nsfc`、`bensz-paper`、`bensz-thesis`、`bensz-cv` 提供了统一的字体定位方式、统一的字体配置宏，以及安装/构建/发布阶段的一致运行时入口。

## 核心定位

`bensz-fonts` 主要做四件事：

- 集中托管外置字体文件，避免各产品线重复拷贝同一批字体
- 提供统一字体路径 API，避免下游包手写硬编码路径
- 提供可复用的字体配置宏，避免 NSFC/CV/Thesis 各自重复写 `fontspec` / `xeCJK` 逻辑
- 作为共享依赖接入安装器、构建器和 Release 打包流程，保证本地、仓库内、Overleaf 三种场景口径一致

## 第一层：源码层如何支撑其它包

### 1. 统一提供字体根目录与文件定位 API

`packages/bensz-fonts/bensz-fonts.sty` 使用 `currfile` 先解析出当前 `bensz-fonts.sty` 的绝对目录，再暴露两个基础接口：

- `\BenszFontsDir`：返回 `fonts/` 目录
- `\BenszFontsFile{<文件名>}`：返回某个字体文件的完整路径

这意味着下游包不需要知道仓库结构、安装位置或 `TEXMFHOME` 真实路径，只要 `\RequirePackage{bensz-fonts}` 成功，后续就能通过统一接口访问字体文件。

### 2. 统一提供“可直接调用”的字体配置宏

`bensz-fonts.sty` 没有把逻辑停留在“路径解析”这一层，而是继续向上封装了多组可复用宏：

- `\BenszFontsSetupNSFCBundled`
  用于 NSFC 模板的一套成品配置，负责楷体、Times New Roman fallback、标题字族与正文 CJK 字体设置。
- `\BenszFontsSetupCVResumeMain`
  用于 `resume.cls` 的英文字体主配置。
- `\BenszFontsSetupCVNotoSansSC`
  用于 CV 的 Noto Sans SC 中文方案。
- `\BenszFontsSetupCVNotoSerifCJKsc`
  用于 CV 的 Noto Serif CJK SC 中文方案。
- `\BenszFontsSetupCVAdobeExternal`
  用于 CV 的 Adobe 中文字体方案。
- `\BenszFontsSetMainTimesFallback`
  统一处理 `Times New Roman -> bundled TimesNewRoman.ttf -> TeX Gyre Termes` 的 fallback。
- `\BenszFontsUseTimesFallback`
  提供可在局部字号/命令中复用的 Times fallback 字体调用。

这样下游包复用的是“稳定 API”，而不是复制一整段 `fontspec` 代码。

## 第二层：各公共包如何接入

### NSFC

`bensz-nsfc` 是当前对 `bensz-fonts` 接入最深的一条产品线：

- `packages/bensz-nsfc/bensz-nsfc-common.sty` 会在检测到 `bensz-fonts.sty` 时主动加载它
- `packages/bensz-nsfc/bensz-nsfc-typography.sty` 优先调用 `\BenszFontsSetupNSFCBundled`
- `packages/bensz-nsfc/scripts/nsfc_project_tool.py` 构建时会把 `packages/bensz-fonts/` 加入 `TEXINPUTS`
- 同一个脚本还会生成 `bensz-nsfc-runtime.def`，把 `\NSFCAssetFontsDir` 指向 `bensz-fonts/fonts/`

结果是：NSFC 模板本身不再维护一份独立字体副本，而是通过 `bensz-fonts` 拿到统一字体路径与配置。

### CV

`bensz-cv` 对 `bensz-fonts` 的依赖最直接：

- `packages/bensz-cv/bensz-cv.cls` 直接 `\RequirePackage{bensz-fonts}`
- `resume.cls` 调用 `\BenszFontsSetupCVResumeMain`
- `NotoSansSC_external.sty`、`NotoSerifCJKsc_external.sty`、`zh_CN-Adobefonts_external.sty` 分别调用对应的 `BenszFontsSetup...` 宏
- `fontawesome.sty` 直接复用 `\BenszFontsDir` 指向图标字体文件

也就是说，CV 包不仅复用了中文/英文字体配置，还复用了图标字体路径能力。

### Thesis

`bensz-thesis` 目前主要复用 `bensz-fonts` 的 fallback 与运行时解析能力：

- `packages/bensz-thesis/bensz-thesis.sty` 在可用时加载 `bensz-fonts`
- `packages/bensz-thesis/styles/bthesis-style-thesis-sysu-doctor.tex` 调用 `\BenszFontsSetMainTimesFallback` 和 `\BenszFontsUseTimesFallback`
- `packages/bensz-thesis/scripts/thesis_project_tool.py` 构建时把 `packages/bensz-fonts/` 注入 `TEXINPUTS`

因此 thesis 不需要自己维护 `TimesNewRoman.ttf` 的查找逻辑。

### Paper

`bensz-paper` 当前对 `bensz-fonts` 的接入偏“基础设施层”：

- `packages/bensz-paper/bensz-paper.sty` 在检测到 `bensz-fonts.sty` 时加载它
- `packages/bensz-paper/scripts/package/install.py` 把 `bensz-fonts` 作为强制依赖
- `packages/bensz-paper/scripts/manuscript_tool.py` 构建时会把 `packages/bensz-fonts/` 追加到 `TEXINPUTS`

当前 `scripts/pack_release.py` 里 `paper` 分支的 `select_overleaf_font_files()` 返回空集合，说明现阶段 SCI 示例链路还没有额外依赖需要随 Overleaf 包注入的外置字体文件；但安装、构建和统一运行时入口已经提前接好了。

## 第三层：安装、构建、发布阶段如何支撑

### 1. 安装阶段：作为共享依赖自动补齐

根级统一安装器 `scripts/install.py` 把 `bensz-fonts` 设为：

- `bensz-nsfc` 的依赖
- `bensz-paper` 的依赖
- `bensz-thesis` 的依赖
- `bensz-cv` 的依赖

因此用户安装这些包时，不需要自己额外判断字体包是否要单独安装；依赖会自动展开。

与此同时，`bensz-paper`、`bensz-thesis`、`bensz-cv` 的包级安装脚本也都保留了 `DEPENDENCY_PACKAGE_NAMES = ("bensz-fonts",)`，确保仓库内和独立安装脚本两种入口口径一致。

### 2. 构建阶段：统一注入 `TEXINPUTS`

仓库内官方构建脚本并不是依赖“当前工作目录刚好能找到字体文件”，而是显式把 `bensz-fonts` 目录加入 `TEXINPUTS`：

- `packages/bensz-nsfc/scripts/nsfc_project_tool.py`
- `packages/bensz-paper/scripts/manuscript_tool.py`
- `packages/bensz-thesis/scripts/thesis_project_tool.py`
- `packages/bensz-cv/scripts/cv_project_tool.py`

这样无论字体包在仓库中、在 `TEXMFHOME` 中，还是在临时构建根里，只要脚本把路径接入了 `TEXINPUTS`，LaTeX 侧就能按统一方式找到 `bensz-fonts.sty` 与 `fonts/`。

### 3. 发布阶段：按项目最小集注入 Overleaf runtime

`scripts/pack_release.py` 没有粗暴地把整个 `bensz-fonts/fonts/` 全量塞进每个 Overleaf zip，而是做了两步：

1. 先按项目类型判断实际需要哪些字体文件
2. 再把 `bensz-fonts.sty` 和所需最小字体子集写入压缩包

当前规则大致是：

- NSFC：注入 `Kaiti.ttf` 与 `TimesNewRoman.ttf`
- Thesis（中大博士示例）：按模板需要注入 `TimesNewRoman.ttf`
- CV：按外置字体方案动态注入 Noto / Adobe / FontAwesome / TeX Gyre Termes 等字体
- Paper：当前不注入额外外置字体

这让 Overleaf 包保持“可直接编译”，同时避免每个项目都携带整套共享字体文件。

### 4. TDS 打包阶段：可随主包一起分发

例如 `packages/bensz-nsfc/scripts/build_tds_zip.py` 在打 `bensz-nsfc` 的 TDS zip 时，会把 `bensz-fonts` 一并纳入压缩包。这样用户安装 NSFC 包时，可以同步得到字体基础包，而不需要手动再补另一套 TDS。

## 为什么必须单独拆成 `bensz-fonts`

如果不拆出 `bensz-fonts`，常见问题会立刻出现：

- 同一字体会在 `bensz-nsfc`、`bensz-cv`、`projects/` 中多处重复存放
- 路径写法会分裂成仓库相对路径、安装后路径、Overleaf 路径三套口径
- 每条产品线都要重复维护一份 `fontspec` / `xeCJK` fallback 逻辑
- Release 体积会持续膨胀，且更难做“按项目最小字体集”裁剪

拆分后，字体资源的单一真相来源就是 `packages/bensz-fonts/`，下游包只关心“调用哪个 API”，而不再关心“字体文件到底放哪”。

## 维护者修改时的建议

如果后续要改 `bensz-fonts`，建议按下面顺序检查：

1. 先判断是“新增字体文件”还是“新增/修改字体 API”
2. 若新增字体文件，同时检查是否需要更新 `scripts/pack_release.py` 的最小字体集选择逻辑
3. 若修改宏名或字体 fallback 行为，同时检查 `bensz-nsfc`、`bensz-cv`、`bensz-thesis` 的调用点
4. 若改动影响安装或分发，再检查根级 `scripts/install.py` 与各包级安装/TDS 脚本
5. 最后优先走官方入口验证，而不是只跑裸 `xelatex`

建议的验证入口：

- NSFC：`python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General`
- Paper：`python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01`
- Thesis：`python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master`
- CV：`python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all`

## 一句话总结

`bensz-fonts` 支撑其它包的方式，可以概括为：

“把字体文件、字体路径解析、字体配置宏、安装依赖、构建时路径注入、Release/Overleaf 打包，统一收口到一个共享基础包里。”
