$out_dir = 'build';
$pdf_mode = 5; # 用xelatex生成pdf
# -synctex=1 生成SyncTex文件
# -interaction=nonstopmode 遇到错误时不等待用户输入而尽可能继续编译
# -shell-escape 编译器调用外部程序
# -file-line-error 编译器报告错误时给出文件名和行号而不是页码
# !如果build下缺少相应文件夹, 这样写本身是会编译失败的, 但LaTeX Workshop似乎会自动创建相应文件夹修复了这个问题
# 见: https://tex.stackexchange.com/a/206986
$xelatex = 'xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape %O %S';
$postscript_mode = $dvi_mode = 0;

push @generated_exts, 'loa', 'bbl', 'run.xml', 'glstex', 'glg';
$clean_ext .= ' loa %R.bbl run.xml glstex glg'; # .=是将值添加到原本字符串末尾

################################################################################
# Implementing glossary with bib2gls and glossaries-extra, with the
#  log file (.glg) analyzed to get dependence on a .bib file.
# !!! ONLY WORKS WITH VERSION 4.54 or higher of latexmk
# 摘自 https://ctan.mirror.twds.com.tw/tex-archive/support/latexmk/example_rcfiles/bib2gls_latexmkrc
add_cus_dep('aux', 'glstex', 0, 'run_bib2gls');

sub run_bib2gls {
    my ($base, $path) = fileparse( $_[0] );
    my $silent_command = $silent ? "--silent" : "";
    my $encoding_args = "--log-encoding UTF-8 --tex-encoding UTF-8";
    if ( $path ) {
        my $ret = system("bib2gls $silent_command $encoding_args -d \"$path\" --group \"$base\"");
    } else {
        my $ret = system("bib2gls $silent_command $encoding_args --group \"$_[0]\"");
    };

    # Analyze log file.
    local *LOG;
    $LOG = "$_[0].glg";
    if (!$ret && -e $LOG) {
        open LOG, "<$LOG";
        while (<LOG>) {
            if (/^Reading (.*\.bib)\s$/) {
                rdb_ensure_file( $rule, $1 );
            }
        }
	    close LOG;
    }
    return $ret;
}

# For the minted package (which does nice formatting of source code):
# 3. In some cases, latexmk does an extra run of *latex than is
#    needed.  This is solved by getting latexmk to ignore certain lines in
#    the aux file when latexmk looks for changes.  These lines are written
#    by minted and are irrelevant to the output file from *latex.
#
#    The reason for the extra run of *latex that may happen is because
#    after minted runs pygmentize to make the nicely formatted source code,
#    minted saves cached information about the run(s) of pygmentize. This
#    information is  put in the aux file. So latexmk sees the changed aux
#    file, and knows that may affect the output of *latex, which it
#    therefore reruns. However the minted-written lines do not affect the
#    output of *latex.
# 摘自 https://mirror-hk.koddos.net/CTAN/support/latexmk/example_rcfiles/minted_latexmkrc
$hash_calc_ignore_pattern{aux} = '^\\\\gdef\\\\minted@oldcachelist\{,'.
                                 '|^\s*default\.pygstyle,'.
                                 '|^\s*[[:xdigit:]]+\.pygtex';
