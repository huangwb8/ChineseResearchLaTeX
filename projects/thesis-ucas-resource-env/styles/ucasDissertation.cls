% ucasDissertation文档类

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{styles/ucasDissertation}[中国科学院大学硕博学位论文LaTeX模板]

\RequirePackage{styles/ucasSilence} % 抑制字体相关的警告, 需要放在加载ctexbook前
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 解析选项
\RequirePackage{kvoptions}
\SetupKeyvalOptions{
    family = UCAS,
    prefix = UCAS@,
    setkeys=\kvsetkeys,
}
\DeclareBoolOption[false]{print} % 印刷版/电子版 (电子版非另页右页, 仅另页), 默认为电子版
\DeclareBoolOption[false]{colorlinks} % 超链接是否彩色, 默认false, 此时为黑色无边框
\DeclareBoolOption[false]{bibBackref} % 是否在参考文献列表中显示文献引用页, 默认false, 此时为不显示
\DeclareVoidOption{draft}{
    \special{xdvipdfmx:config z 0} % 将pdf压缩等级设为0, 缩短生成时间 (但会导致pdf更大)
    \PassOptionsToClass{draft}{ctexbook}
}
\DeclareDefaultOption{\expandafter\PassOptionsToClass\expandafter{\CurrentOption}{ctexbook}} % 将所有未知选项传递给ctexbook类
\ProcessKeyvalOptions*\relax % 执行上面为每个选项定义的代码

\ifUCAS@print
    \PassOptionsToClass{openright}{ctexbook} % 印刷及装订要求中要求另页右页
\else
    \PassOptionsToClass{openany}{ctexbook} % 给book类传递openany选项, 章节不强制 (右页) 奇数页开始
\fi
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 0. 纸张要求和页面设置
\LoadClass[
    scheme = plain, % ctex宏包仅用于提供中文支持, 不对文章排版进行任何修改
    zihao = -4, % 设置文档字号为小四, 也就是12bp. 见ctex文档表: 标准字体命令与字号的对应
    autoindent = true, % 段首缩进2汉字符
    linespread = 1.25, % 1.25倍行距
]{ctexbook}

% 汉化
\ctexset{
    contentsname = {目\quad 录},
    listfigurename = {图目录},
    listtablename = {表目录},
    appendixname = {附录},
    bibname = {参考文献},
}

% 页面设置 ---------------------------------------------------------------------
\RequirePackage[
    a4paper, % 纸张大小
    top = 2.54cm,
    bottom = 2.54cm,
    left = 3.17cm,
    right = 3.17cm,
    % showcrop,
    % showframe, % 用线框可视化显示当前布局各边距大小
]{geometry}
\RequirePackage{setspace}

% 页眉页脚 ----------------------------------------------------------------------
% Word相对于纸张边缘计算而LaTeX相对于版心计算
% 页眉顶端距离= top - headheight - headsep
\geometry{
    headheight=0.51cm, % 页眉高度
    headsep=0.53cm, % 页眉与正文间距
    footskip=1.04cm, % 页脚底端距离= bottom - footskip
}

\RequirePackage{fancyhdr}
\pagestyle{fancy}
\renewcommand{\chaptermark}[1]{\markboth{\UCAS@title@cn}{\CTEXifname{\CTEXthechapter}{}\quad#1}} % 每到新的章节更新左右mark
\renewcommand{\sectionmark}[1]{\empty}

% 正文页眉页脚样式
\fancypagestyle{mainmatter}{
    \fancyhf{} % 清除当前页眉页脚样式
    \fancyhead[CO]{\songti\zihao{-5}\rightmark} % 奇数页页眉为章节名, 宋体小五
    \fancyhead[CE]{\songti\zihao{-5}\leftmark} % 偶数页页眉为论文题目, 宋体小五
    \fancyfoot[LE, RO]{\zihao{-5}\thepage}
}

% 前言页码样式
\fancypagestyle{frontmatter}[mainmatter]{
    \fancyfoot{}
    \fancyfoot[C]{\zihao{-5}\thepage}
}

% 默认字体 ---------------------------------------------------------------------
% ctex默认衬线字体为宋体, 无衬线字体 (\sffamily) 为黑体
\RequirePackage{fontspec}
\setmainfont{Times New Roman} % 设置英文及阿拉伯数字字体

% 按文档结构设置样式 ------------------------------------------------------------
\renewcommand{\frontmatter}{
    \@mainmatterfalse % 导致章节不编号但计入目录
    \pagenumbering{Roman} % 大写罗马数字页码
    \pagestyle{frontmatter}
    \ctexset{chapter/pagestyle = frontmatter} % 章节页眉页脚样式
}

\renewcommand{\mainmatter}{
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \@mainmattertrue
    \pagenumbering{arabic} % 切换为阿拉伯数字页码, 由其他数字切换会导致页码重置
    \pagestyle{mainmatter}
    \ctexset{chapter/pagestyle = mainmatter} % 章节页眉页脚样式
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 1. 封面

% 加载论文信息变量设置命令 -----------------------------------------------------------
\RequirePackage{styles/ucasInfo}

% 增强下划线样式 ----------------------------------------------------------------
\RequirePackage[normalem]{ulem} % 支持复杂内容的下划线\uline{}
\RequirePackage{xeCJKfntef} % 修复uline, 支持中文自动折行

\newcommand{\cnTitleUline}[1]{ % 增大了下划线与文字间距离, 加粗下划线
    \renewcommand{\ULthickness}{1.8pt}
    \setlength{\ULdepth}{0.5em}
    \uline{#1}
    \renewcommand{\ULthickness}{1pt}
}
\newcommand{\enTitleUline}[1]{
    \renewcommand{\ULthickness}{1.8pt}
    \setlength{\ULdepth}{0.4em}
    \expandafter\uline\expandafter{#1} % 修复uline对含可折行字符的文本无法自动折行问题
    \renewcommand{\ULthickness}{1pt}
}
\newcommand{\expandedUline}[1]{\renewcommand{\ULthickness}{1pt}\uline{\hfill #1\hfill}}

% 中文封面 ---------------------------------------------------------------------
\newcommand{\makeCover@cn}{
    \pagestyle{empty} % 首页无页眉页脚
    \begin{center}
        \vspace*{36pt}
        \includegraphics[scale=0.098]{ucas_logo}\par
        \vspace{28pt}
        {\heiti\zihao{1}\UCAS@degree@cn 学位论文\par}
        \vspace{48pt}

        \begin{spacing}{1}{\heiti\zihao{-3}\textbf{\cnTitleUline{\UCAS@title@cn}}}\end{spacing}\par

        \vspace{61pt}\par
        \begin{spacing}{2}
            \bfseries
            \zihao{4}\noindent\begin{tabularx}{\textwidth}{lXp{3.5em}} % 第三列设置成和第一列差不多宽，让第二列能居中
                作者姓名: & \expandedUline{\UCAS@author@cn} & \\
                指导教师: & \expandedUline{\UCAS@supervisor@cn} & \\
                         & \expandedUline{\UCAS@supervisor@institute} & \\
                学位类别: & \expandedUline{\UCAS@degreeType@cn} & \\
                学科专业: & \expandedUline{\UCAS@subject@cn} & \\
                培养单位: & \expandedUline{\UCAS@institute@cn} & \\
            \end{tabularx}\par
            \vspace{72pt}
            \UCAS@gradYear 年\UCAS@gradMonth@cn 月
        \end{spacing}
    \end{center}
}

% 英文封面 ---------------------------------------------------------------------
\newcommand{\makeCover@en}{
    \pagestyle{empty}
    \begin{center}
        \vspace*{58pt}
        % 由于下划线位置较低, 设置1.3倍行距, 在标题有多行时上下看着不会太挤
        \begin{spacing}{1.3}{\zihao{-3}\textbf{\enTitleUline{\UCAS@title@en}}}\end{spacing}

        \vspace{80pt}

        \begin{spacing}{2}
            \bfseries\zihao{4}
            A \UCAS@articleType\ submitted to\\
            University of Chinese Academy of Sciences\\
            in partial fulfillment of the requirement\\
            for the degree of\\
            \UCAS@degreeType@en\\
            in \UCAS@subject@en\\
            By\\
            \UCAS@author@en\\
            Supervisor:\quad\UCAS@supervisor@en\\
            \vspace{73pt}
            \UCAS@institute@en\\
            \UCAS@gradMonth@en~\UCAS@gradYear
        \end{spacing}
    \end{center}
}

% 中国科学院大学规定的统一中英文封面 ----------------------------------------------
\newcommand{\makeCover}{
    \makeCover@cn
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \makeCover@en
    \global\let\makeCover\relax % 销毁该命令, 防止重复调用
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 2. 原创性声明及授权使用声明
\newcommand{\makeDeclaration}{
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \pagestyle{empty}
    \begin{spacing}{1.5}
        \vspace*{48pt}
        {\centering\heiti\zihao{4}\textbf{中国科学院大学\\研究生学位论文原创性声明}\par}

        \songti\zihao{-4}
        \vspace{\baselineskip}
        本人郑重声明：所呈交的学位论文是本人在导师的指导下独立进行研究工作所取得
        的成果。承诺除文中已经注明引用的内容外，本论文不包含任何其他个人或集体享
        有著作权的研究成果，未在以往任何学位申请中全部或部分提交。对本论文所涉及
        的研究工作做出贡献的其他个人或集体，均已在文中以明确方式标明或致谢。本人
        完全意识到本声明的法律结果由本人承担。

        \vspace{\baselineskip}

        \hspace{21.5\ccwd}作者签名:\par
        \hspace{21.5\ccwd}日\quad\quad 期:\par

        \vspace{48pt}

        {\centering\heiti\zihao{4}\textbf{中国科学院大学\\学位论文使用授权声明}\par}

        \songti\zihao{-4}
        \vspace{\baselineskip}
        本人完全了解并同意遵守中国科学院大学有关收集、保存和使用学位论文的规定，
        即中国科学院大学有权按照学术研究公开原则和保护知识产权的原则， 保留并向
        国家指定或中国科学院指定机构送交学位论文的电子版和印刷版文件，且电子版与
        印刷版内容应完全相同，允许该论文被检索、查阅和借阅，公布本学位论文的全部
        或部分内容，可以采用扫描、影印、缩印等复制手段以及其他法律许可的方式保
        存、汇编本学位论文。

        涉密及延迟公开的学位论文在解密或延迟期后适用本声明。

        \vspace{\baselineskip}

        {\centering
            作者签名:\hspace{12\ccwd}导师签名:\\
            日\quad\quad 期:\hspace{12\ccwd}日\quad\quad 期:\par
        }
    \end{spacing}
    \global\let\makeDeclaration\relax % 销毁该命令, 防止重复调用
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 3. 书脊
% 在ucasSpine.cls
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 4. 摘要和关键词
\newcommand{\abstract}[2]{
    \newcommand{\UCAS@abstract@cn}{#1}
    \newcommand{\UCAS@abstract@en}{#2}
}
\newcommand{\keywords}[2]{
    \newcommand{\UCAS@keywords@cn}{#1}
    \newcommand{\UCAS@keywords@en}{#2}
}
\newcommand{\makeAbstract}{
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    %这样写是为了这些章节不出现在\tableofcontents命令给出的目录中，但出现在pdf书签目录中
    \currentpdfbookmark{摘要}{摘要} % 添加pdf书签. 前一个参数是书签名, 后一个是内部标识
    \chapter*{
        \markboth{\UCAS@title@cn}{摘\quad 要} % 左右mark都设置为章节名, 使其出现在页眉
        摘\quad 要
    }
    \UCAS@abstract@cn\par
    \vspace{\baselineskip}\par % 关键词与摘要间空一行
    \noindent\textbf{关键词:}\ \UCAS@keywords@cn

    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \currentpdfbookmark{Abstract}{Abstract}
    \chapter*{
        \markboth{\UCAS@title@en}{Abstract}
        Abstract
    }
    \UCAS@abstract@en\par
    \vspace{\baselineskip}\par
    \noindent\textbf{Key Words:}\ \UCAS@keywords@en

    \global\let\makeAbstract\relax % 销毁该命令, 防止重复调用
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 5. 目录

% 设置目录项样式 ----------------------------------------------------------------
\RequirePackage[
    titles % 目录, 图表目录的标题以LaTeX默认方法排版, 此处为\ctexset设置的章节标题的样式
]{tocloft} % 用于自定义目录样式
\renewcommand{\cftdot}{\ensuremath{\cdot}} % 目录中间的点用居中的
\renewcommand{\@dotsep}{1} % 目录中间的点的间距
\renewcommand{\cftdotsep}{\@dotsep}
% 章目录
\renewcommand{\cftchapleader}{\cftdotfill{\cftdotsep}} % 强制章节名与页码间也是点
\setlength{\cftbeforechapskip}{6pt} % 段前距
\renewcommand{\cftchapfont}{\heiti\zihao{4}\linespread{1.0}} % 黑体四号单倍行距
% 二级标题目录
\setlength{\cftbeforesecskip}{6pt}
\renewcommand{\cftsecfont}{\heiti\zihao{-4}\linespread{1.0}} % 黑体小四号单倍行距
\renewcommand{\cftsecindent}{1\ccwd}
% 三级标题目录
\setlength{\cftbeforesubsecskip}{6pt}
\renewcommand{\cftsubsecfont}{\heiti\zihao{-4}\linespread{1.0}} % 黑体小四号单倍行距
\renewcommand{\cftsubsecindent}{2\ccwd}
% 图/表/算法/代码目录

% 使设置\listoffigures样式的命令也能设置\listofalgorithms样式
% 见: https://tex.stackexchange.com/a/186135
\RequirePackage{algorithm}
\RequirePackage{etoolbox}
\patchcmd{\listof}% <cmd>
{\float@listhead}% <search>
{\@namedef{l@#1}{\l@figure}\float@listhead}% <replace>
{}{}% <success><failure>

\setlength{\cftbeforefigskip}{6pt}
\setlength{\cftbeforetabskip}{6pt}
\renewcommand{\cftfigfont}{\heiti\zihao{4}\linespread{1.0}} % 黑体四号单倍行距
\renewcommand{\cfttabfont}{\heiti\zihao{4}\linespread{1.0}} % 黑体四号单倍行距

% 修改列出目录命令 --------------------------------------------------------------
% 改\tableofcontents
\let\oldtableofcontents\tableofcontents
\renewcommand{\tableofcontents}{
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \currentpdfbookmark{目录}{目录}
    \oldtableofcontents
    \markboth{\UCAS@title@cn}{} % 修改目录命令中设定的左页眉
}
% 四种材料的目录和为\listofmaterials命令
\RequirePackage{keyval}
\define@key{listofmaterials}{table}[true]{\def\listTable{#1}}
\define@key{listofmaterials}{figure}[true]{\def\listFigure{#1}}
\define@key{listofmaterials}{algorithm}[true]{\def\listAlgorithm{#1}}
\define@key{listofmaterials}{code}[true]{\def\listCode{#1}}
\newcommand{\listofmaterials}[1][]{ % 图表目录, 列出图, 表, 算法, 代码
    \SetupFloatingEnvironment{listing}{listname=代码目录}
    \renewcommand{\listalgorithmname}{算法目录}
    % 处理选项
    \def\listTable{false}
    \def\listFigure{false}
    \def\listAlgorithm{false}
    \def\listCode{false}
    \setkeys{listofmaterials}{#1}

    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \ctexset{chapter/break={}} % 下面几个章节不另起一页
    \markboth{\UCAS@title@cn}{图表目录}
    \currentpdfbookmark{图表目录}{图表目录}
    %防止页眉页脚中的标记被自动更新
    \let\oldmarkboth\@mkboth
    \renewcommand{\@mkboth}[2]{}

    \ifthenelse{\equal{\listFigure}{true}}{\listoffigures}{}
    \ifthenelse{\equal{\listTable}{true}}{\listoftables}{}
    \ifthenelse{\equal{\listAlgorithm}{true}}{\listofalgorithms}{}
    \ifthenelse{\equal{\listCode}{true}}{\listoflistings}{}

    \let\@mkboth\oldmarkboth
    \ctexset{chapter/break=\if@openright\cleardoublepage\else\clearpage\fi}
    \global\let\listofmaterials\relax
}
% 改\printunsrtglossary
\newcommand{\listofnotaions}{
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \currentpdfbookmark{术语表}{术语表}
    \chapter*{
        \markboth{\UCAS@title@cn}{术语表}
        术语表
    }
    %printunsrtglossary会自动调用\markboth，需要禁止
    \let\oldmarkboth\@mkboth
    \renewcommand{\@mkboth}[2]{}

    \printunsrtglossary[type=symbols]
    \printunsrtglossary[type=abbreviations]

    \let\@mkboth\oldmarkboth
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 6. 正文

% 各级文本样式 ------------------------------------------------------------------
\ctexset{
    chapter = { % 章标题
      name={第,章},
      nameformat = {}, % 清除标题编号样式
      titleformat = {}, % 清除标题内容样式
      aftername = \quad, % 序号与题名之间空一个汉字符
      format= \heiti\zihao{4}\bfseries\centering\linespread{1.0}, % 黑体四号加粗居中单倍行距
      beforeskip = 24pt, % 段前距
      afterskip = 18pt, % 段后距
      fixskip = true, % 抑制段前段后距以外的多余垂直间距
      afterindent = true, % 标题后首段首行缩进
     },
    section = { % 二级标题
      nameformat = {},
      titleformat = {},
      aftername = \quad,
      format= \heiti\zihao{-4}\linespread{1.0},
      beforeskip = 24pt,
      afterskip = 6pt,
      fixskip = true,
      afterindent = true,
     },
    subsection = { % 三级标题
            nameformat = {},
            titleformat = {},
            aftername = \quad,
            format= \heiti\zihao{-4}\linespread{1.0},
            beforeskip = 12pt,
            afterskip = 6pt,
            fixskip = true,
            afterindent = true,
        },
    subsubsection = { % 四级标题
            nameformat = {},
            titleformat = {},
            aftername = \quad,
            format= \heiti\zihao{-4}\linespread{1.0},
            beforeskip = 12pt,
            afterskip = 6pt,
            fixskip = true,
            afterindent = true,
        },
    paragraph/afterindent = true, % 段首缩进
    subparagraph/afterindent = true,
    appendix = {
            name = {附录},
            number = \chinese{chapter},
        },
}
% 文档默认样式即段落文字样式

\ctexset{secnumdepth=subsubsection} % 正文中对最多四级的标题编号, 更深的标题不编号

%列表 --------------------------------------------------------------------------
% 设置无序列表标签样式
\renewcommand{\labelitemi}{\(\bullet\)}
\renewcommand{\labelitemii}{\(\circ\)}
\renewcommand{\labelitemiii}{\(\circ\)}
\renewcommand{\labelitemiv}{\(\circ\)}
% 设置有序/无序列表的标签左对齐, 与正文一致
\RequirePackage{enumitem}
% 有序列表列表项首行缩进4字符（使序号大致缩进2字符），后续行无缩进，序号与列表项间无间隔，序号样式为（1）
\setlist[enumerate]{itemindent=4\ccwd, leftmargin=0pt, labelsep=0pt, label=（\arabic*）}
% 无序列表列表项首行缩进3字符，后续行无缩进，标签与列表项间3字符（使圆点大致处于左边界起第3字符的中间），标签样式为实心圆
\setlist[itemize]{itemindent=3\ccwd, leftmargin=0pt, labelsep=3pt}
% 列表上下及列表项间无额外间距
\setlist{nosep}

% 图 ---------------------------------------------------------------------------
\RequirePackage{float}
\floatplacement{figure}{htb} % 图的默认位置: 优先放在当前位置, 其次放在页面顶部, 再次放在页面底部
\appto\figure{\centering\zihao{5}} % 图居中
\RequirePackage{graphicx}
\graphicspath{{assets}}
\RequirePackage{subcaption} % 提供子图环境subfigure

% tikz绘图
\RequirePackage{tikz}

% 表 ---------------------------------------------------------------------------
\floatplacement{table}{htb}
\appto\table{\centering\zihao{5}} % 表居中, 表格内字体五号
% 行间距1.5倍 (得自word模板实现)
% TODO: 卧排表顶左底右, 即表顶朝左
\RequirePackage{tabularx}
\RequirePackage{booktabs} % 提供\toprule, \midrule, \bottomrule
% TODO: 表的样式, 封装图表命令

% 表达式 (公式) -----------------------------------------------------------------
\RequirePackage{amsmath}
\RequirePackage{amssymb}
\RequirePackage{unicode-math}
\everydisplay{\zihao{5}} % 显示公式的表达式及右侧编号为五号Times New Roman
\usepackage{gensymb} % 提供一些科学和数学中常用的通用符号，如单位符号

% 算法环境 ---------------------------------------------------------------------
\RequirePackage{algpseudocode}
\renewcommand{\algorithmicrequire}{\textbf{输入：}}
\renewcommand{\algorithmicensure}{\textbf{输出：}}
\renewcommand{\algorithmicif}{\textbf{如果}}
\renewcommand{\algorithmicthen}{\textbf{则}}
\renewcommand{\algorithmicelse}{\textbf{否则}}
\renewcommand{\algorithmicfor}{\textbf{对于}}
\renewcommand{\algorithmicforall}{\textbf{对于所有}}
\renewcommand{\algorithmicdo}{\textbf{执行}}
\renewcommand{\algorithmicwhile}{\textbf{当}}
\renewcommand{\algorithmicloop}{\textbf{循环}}
\renewcommand{\algorithmicrepeat}{\textbf{重复}}
\renewcommand{\algorithmicuntil}{\textbf{直到}}
\renewcommand{\algorithmicreturn}{\textbf{返回}}
\renewcommand{\algorithmicend}{\textbf{结束}}
\renewcommand{\algorithmicprocedure}{\textbf{过程}}
\renewcommand{\algorithmicfunction}{\textbf{函数}}
% algorithmicx自带的拼接end与xx的方式给出的汉化不好看，直接更改结束命令显示文本
\algrenewtext{EndIf}{\textbf{结束如果}}
\algrenewtext{EndFor}{\textbf{结束循环}}
\algrenewtext{EndWhile}{\textbf{结束循环}}

% 代码环境 ---------------------------------------------------------------------
\RequirePackage[svgnames]{xcolor}
\RequirePackage[
    cachedir=minted_cache,
    newfloat,
]{minted}
\setminted{
    breaklines,
    linenos,
    fontsize=\footnotesize,
    frame=single,
}
\let\oldmint\mint
\renewcommand{\mint}[3][]{\oldmint[frame=none,linenos=false,#1]{#2}{#3}}

% 题注 ---------------------------------------------------------------
\RequirePackage[list=off]{bicaption} % 图表目录中仅显示第一语言的标题
\captionsetup{
    labelsep=quad, % 图/表序与图/表题文字之间空一个汉字符
    skip=0pt, % 题注与上文及下文的距离 (其实是设置与下文间距为0)
    aboveskip=0.5em, % 题注与上文的距离
}
\DeclareCaptionFormat{cn}{\vspace{6pt}\songti\zihao{5}\bfseries\linespread{1.25}#1#2#3\par} % 中文图/表题样式: 宋体五号加粗1.25倍行距, 段前6pt段后0pt
\DeclareCaptionFormat{en}{\zihao{5}\bfseries\linespread{1.25}#1#2#3\vspace{12pt}\par} % 英文图/表题样式: Times New Roman五号加粗1.25倍行距, 段前6pt段后0pt
\captionsetup[bi-first]{format=cn, justification=raggedright, singlelinecheck=true}
\captionsetup[bi-second]{format=en, justification=raggedright, singlelinecheck=true}
\captionsetup[figure][bi-first]{name={图}}
\captionsetup[table][bi-first]{name={表}}
\captionsetup[listing][bi-first]{name={代码}}
\captionsetup[listing][bi-second]{name={Code}}
\renewcommand{\thefigure}{\thechapter-\arabic{figure}} % 图序号样式: 章节-序号
\renewcommand{\thetable}{\thechapter-\arabic{table}}
\renewcommand{\theequation}{\thechapter-\arabic{equation}}
\renewcommand{\thealgorithm}{\thechapter-\arabic{algorithm}}
% \SetupFloatingEnvironment{listing}{within=none} % 代码环境不随章节编号

\newcommand{\figureautorefname}{图}
\newcommand{\tableautorefname}{表}
\newcommand{\equationautorefname}{公式}
\renewcommand{\listingautorefname}{代码}
\newcommand{\algorithmautorefname}{算法}
\renewcommand{\ALG@name}{算法}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 7. 其他
\RequirePackage[perpage]{footmisc} % 每页脚注编号重新开始

% 参考文献 ----------------------------------------------------------------------
\ifUCAS@bibBackref
  \PassOptionsToPackage{backref=true}{biblatex} % 在参考文献列表中显示文献引用页
\else
  \PassOptionsToPackage{backref=false}{biblatex}
\fi

\RequirePackage[
    backend = biber,
    maxbibnames = 3,
    style = gb7714-2015, % chktex 8 % biblatex-gb7714-2015宏包提供的顺序编码制
    citestyle = gb7714-2015, % chktex 8
    gbnamefmt=lowercase, % 对于bib文件中的作者姓名的大小写不做改变
    gbpub=false, % 放弃国标的要求, 不使用"出版地不详"等补充信息
    doi=false, % 不显示DOI
    defernumbers=true, % 以允许\printbibliography{}的resetnumbers=true选项
]{biblatex}

% 修改\printbibliography页眉样式为和正文一样
\defbibheading{bibintoc}[\bibname]{%
    \chapter*{%
        \markboth{\UCAS@title@cn}{#1}%
        \addcontentsline{toc}{chapter}{#1}%
        #1%
    }%
}

% 附录 -------------------------------------------------------------------------
\let\oldappendix\appendix
\renewcommand{\appendix}{
    \ifUCAS@print\cleardoublepage\else\clearpage\fi
    \oldappendix
    \fancyhead[CO]{\songti\zihao{-5}附\quad 录} % 附录部分页眉为"附录" (没有编号), 两字间空一个汉字符
}

% 致谢 -------------------------------------------------------------------------
\newcommand{\acknowledgementsDate}{\begin{flushright}\UCAS@gradYear 年\UCAS@gradMonth@cn 月\end{flushright}}

% 超链接, pdf元信息及pdf书签 ----------------------------------------------------
\RequirePackage[
    colorlinks,
    linkcolor=RoyalBlue,anchorcolor=black,citecolor=green,urlcolor=orange,
    pdfstartview = FitH,
    bookmarks = true, % 创建pdf书签
    bookmarksopen = true, % 默认显示书签并展开所有级别
    bookmarksdepth=4, % 包含到四级标题
    bookmarksnumbered, % 书签名包含编号
]{hyperref} % 为了不被其他宏包覆盖hyperref对LaTeX内部命令的修改, 尽可能将hyperref置于导言区最后
\ifUCAS@colorlinks
  %
\else
  \hypersetup{hidelinks}  % 隐藏链接颜色和框
\fi

% 符号说明 (术语表) -----------------------------------------------------------------------
\RequirePackage[ % 需要放在hyperref后
    nogroupskip, % 不在每个字母组间添加垂直间距
    record, % 显示术语出现的页码
    toc=false, % 不添加到目录
    nomain, % 不生成不必要的主术语表
    style=long3col,
]{glossaries-extra}

\setglossarysection{section} % 设置术语表标题为章节

% 定义新的缩写样式
\newabbreviationstyle{customstyle}{}{%
  \renewcommand*{\glsxtrfullformat}[1]{%
    \glsentrydesc{##1} (\glsxtrlong{##1}, \glsxtrshort{##1})%
  }%
}
\setabbreviationstyle{customstyle}

% 创建两个术语表
\newglossary*{abbreviations}{缩写}
\newglossary*{symbols}{符号}