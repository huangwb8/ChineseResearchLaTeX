# bensz-fonts

`bensz-fonts` 是 `ChineseResearchLaTeX` 的共享字体基础包。

它负责：

- 集中托管 `bensz-*` 系列模板使用的外置字体文件
- 提供统一的字体路径与字体配置 API
- 作为 `bensz-nsfc`、`bensz-paper`、`bensz-thesis`、`bensz-cv` 的基础依赖

字体文件统一放在单一 `fonts/` 根目录下，不按“模板类型 / 使用场景”再分层，避免把同一字体错误绑定到某一种模板。

## 目录说明

- `bensz-fonts.sty`：统一字体路径与字体配置入口
- `fonts/`：扁平化托管的全部字体文件

## GXNSF 字体

`GXNSF_General` 通过 `\BenszFontsGXNSFSetupFangsongFallback` 与
`\BenszFontsGXNSFSetupKaiFallback` 使用广西自然科学基金项目的字体回退链。
当系统中未安装原始方正字体时，共享包会使用 `FZFangSong-Z02.ttf` 与
`FZKai-Z03.ttf`；再回退到系统微软雅黑和既有的跨平台字体。方正字体的使用、
打包和再分发须遵守相应字体许可。

## 安装

优先使用根级统一安装器：

```bash
python3 scripts/install.py install --packages bensz-fonts
python3 scripts/install.py install --packages bensz-fonts --mirror gitee
```

当安装其它 `bensz-*` 包时，`bensz-fonts` 会作为强制依赖自动一并安装。
