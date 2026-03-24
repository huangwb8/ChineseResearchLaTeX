% ucasSpine文档类, 用于书脊

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{styles/ucasSpine}[中国科学院大学硕博学位论文配套书脊LaTeX模板]

\RequirePackage{styles/ucasSilence} % 抑制字体相关的警告, 需要放在加载ctexbook前
\RequirePackage{styles/ucasInfo} % 加载论文信息变量设置命令

\RequirePackage{xeCJK}
\defaultCJKfontfeatures{RawFeature={vertical:+vert}} % 旋转中文字符

\LoadClass[
    scheme = plain, % ctex宏包仅用于提供中文支持, 不对文章排版进行任何修改
    zihao = -4, % 设置文档字号为小四, 也就是12bp. 见ctex文档表: 标准字体命令与字号的对应
    autoindent = false, % 段首无缩进
    linespread = 1.17, % 似乎按标准行间距该是14磅. 小四字号约为12pt, 1.17倍行间距约为14pt
]{ctexbook}

% 页面设置
\RequirePackage[
    paper=a4paper,
    landscape,
    top=9.5cm,
    bottom=9.5cm,
    left=3cm,
    right=3cm,
    % showframe,
]{geometry}
\geometry{
    headheight=0cm,
    headsep=0cm,
    footskip=0cm,
    marginparsep=0cm,
}
\thispagestyle{empty}

\RequirePackage{fontspec}
\setmainfont{Times New Roman} % 设置英文及阿拉伯数字字体

\newcommand*\CJKmovesymbol[1]{\raise.29em\hbox{#1}}
\newcommand*\CJKmove{
    \punctstyle{plain}
    \let\CJKsymbol\CJKmovesymbol
    \let\CJKpunctsymbol\CJKsymbol
}
\AtBeginDocument{\CJKmove\sloppy} %修正baseline

\usepackage{everypage}
\AddEverypageHook{\special{pdf: put @thispage <</Rotate 90>>}}

\newcommand{\makeSpine}{
    \hspace{0pt}
    \vfill

    \heiti\bfseries % 黑体小四加粗居中
    \raisebox{.7em}{\hspace{-14pt}\parbox{40\ccwd}{\UCAS@title@cn}}
    \hfill
    \raisebox{.7em}{\parbox{5\ccwd}{\UCAS@author@cn}}
    \hfill
    \raisebox{.7em}{\parbox{7\ccwd}{中国科学院大学}}

    \vfill
    \hspace{0pt}
}