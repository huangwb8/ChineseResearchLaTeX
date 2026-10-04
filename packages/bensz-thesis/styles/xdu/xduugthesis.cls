%%
%% This is file `xduugthesis.cls',
%% generated with the docstrip utility.
%%
%% The original source files were:
%%
%% xduts.dtx  (with options: `class,thesis,xduugthesis')
%% 
%% Copyright 2022--2026 by @note286 in GitHub and CTAN
%% 
%% This work may be distributed and/or modified under the
%% conditions of the LaTeX Project Public License, either version 1.3c
%% of this license or (at your option) any later version.
%% The latest version of this license is in
%%   http://www.latex-project.org/lppl.txt
%% and version 1.3c or later is part of all distributions of LaTeX
%% version 2005/12/01 or later.
%% 
%% This work has the LPPL maintenance status `author-maintained'.
%% 
%% The Current Maintainer of this work is @note286 in GitHub and CTAN.
%% 
%% This work consists of the files README.md, xduts.dtx, and xduts.ins
%% and the derived files xduts.pdf, xdufont.sty,
%% xduugtp.cls, xduugthesis.cls, and xdupgthesis.cls.
%% 
%% The copyright of xdulogo.pdf is Xidian University.
%% 
\NeedsTeXFormat{LaTeX2e}
\RequirePackage{expl3}
\ProvidesExplClass{xduugthesis}
  {2025/04/26}{6.2.7.2}
  {Xidian University Undergraduate Thesis document class}
\RequirePackage { xparse, l3keys2e }
\PassOptionsToPackage { no-math } { fontspec }
\PassOptionsToPackage { quiet } { xeCJK }
\PassOptionsToClass
  {
    a4paper,
    zihao=-4,
    sub4section,
    linespread = 1.625,
    fontset    = none
  }
  { ctexbook }
\LoadClass { ctexbook }
\RequirePackage { geometry        }
\geometry       { paper = a4paper }
\RequirePackage { fancyhdr        }
\RequirePackage { xeCJKfntef      }
\RequirePackage { graphicx        }
\tl_new:N \l__xdu_cjk_font_tl
\tl_new:N \l__xdu_fake_bold_tl
\tl_new:N \l__xdu_fake_slant_tl
\tl_new:N \l__xdu_latin_font_tl
\tl_new:N \l__xdu_latin_sans_scale_tl
\tl_new:N \l__xdu_latin_mono_scale_tl
\tl_new:N \l__xdu_math_font_tl
\tl_new:N \l__xdu_unicode_math_tl
\tl_new:N \l__xdu_font_type_tl
\tl_new:N \l__xdu_font_path_tl
\keys_define:nn { xdu / style }
  {
    cjk-font .choices:nn =
      { win, adobe, founder, hanyi, sinotype, fandol, none }
      { \tl_set_eq:NN \l__xdu_cjk_font_tl \l_keys_choice_tl },
    cjk-fake-bold .tl_set:N = \l__xdu_fake_bold_tl,
    cjk-fake-slant .tl_set:N = \l__xdu_fake_slant_tl,
    latin-sans-scale .choices:nn = { upper, lower, off }
      { \tl_set_eq:NN \l__xdu_latin_sans_scale_tl \l_keys_choice_tl },
    latin-mono-scale .choices:nn = { upper, lower, off }
      { \tl_set_eq:NN \l__xdu_latin_mono_scale_tl \l_keys_choice_tl },
    latin-font .choices:nn = { gyre, tac, tacn, tcc, thcs, tll, none }
      { \tl_set_eq:NN \l__xdu_latin_font_tl \l_keys_choice_tl },
    math-font .choices:nn =
      {
        asana, bonum, cambria, cm, concrete, dejavu, erewhon, euler,
        fira, garamond, gfsneohellenic, kp, libertinus, lm, newcm,
        pagella, schola, stix, stix2, termes, xcharter, xits, none
      }
      { \tl_set_eq:NN \l__xdu_math_font_tl \l_keys_choice_tl },
    unicode-math .tl_set:N = \l__xdu_unicode_math_tl,
    font-type .choices:nn = { font, file }
      { \tl_set_eq:NN \l__xdu_font_type_tl \l_keys_choice_tl },
    font-path .tl_set:N = \l__xdu_font_path_tl
  }
\keys_set:nn { xdu }
  {
    style / cjk-font         = fandol,
    style / cjk-fake-bold    = 3,
    style / cjk-fake-slant   = 0.2,
    style / latin-font       = gyre,
    style / latin-sans-scale = off,
    style / latin-mono-scale = off,
    style / math-font        = cm,
    style / unicode-math     = { },
    style / font-type        = font,
    style / font-path        = fonts
  }
\cs_new:Npn \__xdu_select_font:nn #1#2
  {
    \str_if_eq:NNTF { \l__xdu_font_type_tl } { font }
      { #1 }
      { #2 }
  }
\cs_new:Npn \__xdu_font_path:
  {
    \str_if_eq:NNTF { \l__xdu_font_type_tl } { font }
      { }
      { Path = \l__xdu_font_path_tl / , }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_b:n #1
  {
    BoldFont = { #1 }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_fb:n #1
  {
    BoldFont     = { #1 },
    BoldFeatures = { FakeBold = \l__xdu_fake_bold_tl }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_fs:n #1
  {
    SlantedFont     = { #1 },
    SlantedFeatures = { FakeSlant = \l__xdu_fake_slant_tl }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_fbfs:n #1
  {
    BoldSlantedFont     = { #1 },
    BoldSlantedFeatures =
      {
        FakeBold  = \l__xdu_fake_bold_tl,
        FakeSlant = \l__xdu_fake_slant_tl
      }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_bfs:n #1
  {
    BoldSlantedFont     = { #1 },
    BoldSlantedFeatures = { FakeSlant = \l__xdu_fake_slant_tl }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_i:n #1
  {
    ItalicFont = { #1 }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_fi:n #1
  {
    ItalicFont     = { #1 },
    ItalicFeatures = { FakeSlant = \l__xdu_fake_slant_tl }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_ifb:n #1
  {
    BoldItalicFont     = { #1 },
    BoldItalicFeatures = { FakeBold = \l__xdu_fake_bold_tl }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_sub_fifb:n #1
  {
    BoldItalicFont     = { #1 },
    BoldItalicFeatures =
      {
        FakeBold  = \l__xdu_fake_bold_tl,
        FakeSlant = \l__xdu_fake_slant_tl
      }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_r:n #1
  {
    \__xdu_cfg_cjk_font_sub_fb:n   { #1 },
    \__xdu_cfg_cjk_font_sub_fs:n   { #1 },
    \__xdu_cfg_cjk_font_sub_fbfs:n { #1 },
    \__xdu_cfg_cjk_font_sub_fi:n   { #1 },
    \__xdu_cfg_cjk_font_sub_fifb:n { #1 }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_rb:nn #1#2
  {
    \__xdu_cfg_cjk_font_sub_b:n    { #2 },
    \__xdu_cfg_cjk_font_sub_fs:n   { #1 },
    \__xdu_cfg_cjk_font_sub_bfs:n  { #2 },
    \__xdu_cfg_cjk_font_sub_fi:n   { #1 },
    \__xdu_cfg_cjk_font_sub_fifb:n { #1 }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_ri:nn #1#2
  {
    \__xdu_cfg_cjk_font_sub_fb:n   { #1 },
    \__xdu_cfg_cjk_font_sub_fs:n   { #1 },
    \__xdu_cfg_cjk_font_sub_fbfs:n { #1 },
    \__xdu_cfg_cjk_font_sub_i:n    { #2 },
    \__xdu_cfg_cjk_font_sub_ifb:n  { #2 }
  }
\cs_new:Npn \__xdu_cfg_cjk_font_rbi:nnn #1#2#3
  {
    \__xdu_cfg_cjk_font_sub_b:n   { #2 },
    \__xdu_cfg_cjk_font_sub_fs:n  { #1 },
    \__xdu_cfg_cjk_font_sub_bfs:n { #2 },
    \__xdu_cfg_cjk_font_sub_i:n   { #3 },
    \__xdu_cfg_cjk_font_sub_ifb:n { #3 }
  }
\cs_new:Npn \__xdu_set_cjk_main_font:nn #1#2
  {
    \setCJKmainfont { #1 }
      [ \__xdu_font_path: \__xdu_cfg_cjk_font_ri:nn { #1 } { #2 } ]
  }
\cs_new:Npn \__xdu_set_cjk_main_font:nnn #1#2#3
  {
    \setCJKmainfont { #1 }
      [ \__xdu_font_path: \__xdu_cfg_cjk_font_rbi:nnn { #1 } { #2 } { #3 } ]
  }
\cs_new:Npn \__xdu_set_cjk_sans_font:n #1
  {
    \setCJKsansfont { #1 }
      [ \__xdu_font_path: \__xdu_cfg_cjk_font_r:n { #1 } ]
  }
\cs_new:Npn \__xdu_set_cjk_sans_font:nn #1#2
  {
    \setCJKsansfont { #1 }
      [ \__xdu_font_path: \__xdu_cfg_cjk_font_rb:nn { #1 } { #2 } ]
  }
\cs_new:Npn \__xdu_set_cjk_mono_font:n #1
  {
    \setCJKmonofont { #1 }
      [ \__xdu_font_path: \__xdu_cfg_cjk_font_r:n { #1 } ]
  }
\cs_new:Npn \__xdu_load_cjk_font_win:
  {
    \__xdu_set_cjk_main_font:nn
      { \__xdu_select_font:nn { SimSun   } { simsun.ttc  } }
      { \__xdu_select_font:nn { KaiTi    } { simkai.ttf  } }
    \__xdu_set_cjk_sans_font:n
      { \__xdu_select_font:nn { SimHei   } { simhei.ttf  } }
    \__xdu_set_cjk_mono_font:n
      { \__xdu_select_font:nn { FangSong } { simfang.ttf } }
  }
\cs_new:Npn \__xdu_load_cjk_font_adobe:
  {
    \__xdu_set_cjk_main_font:nn
      { \__xdu_select_font:nn { Adobe~Song~Std     } { adobesongstd-light.otf        } }
      { \__xdu_select_font:nn { Adobe~Kaiti~Std    } { adobekaitistd-regular.otf     } }
    \__xdu_set_cjk_sans_font:n
      { \__xdu_select_font:nn { Adobe~Heiti~Std    } { adobeheitistd-regular.otf     } }
    \__xdu_set_cjk_mono_font:n
      { \__xdu_select_font:nn { Adobe~Fangsong~Std } { Adobe-Fangsong-Std-R-Font.otf } }
  }
\cs_new:Npn \__xdu_load_cjk_font_founder:
  {
    \__xdu_set_cjk_main_font:nn
      { \__xdu_select_font:nn { FZShuSong-Z01  } { FZShuSong-Z01.ttf } }
      { \__xdu_select_font:nn { FZKai-Z03      } { FZKai-Z03.ttf     } }
    \__xdu_set_cjk_sans_font:n
      { \__xdu_select_font:nn { FZHei-B01      } { FZHei-B01.ttf     } }
    \__xdu_set_cjk_mono_font:n
      { \__xdu_select_font:nn { FZFangSong-Z02 } { FZFSK.TTF         } }
  }
\cs_new:Npn \__xdu_load_cjk_font_hanyi:
  {
    \__xdu_set_cjk_main_font:nn
      { \__xdu_select_font:nn { HYShuSongErS } { HYShuSongErS.ttf  } }
      { \__xdu_select_font:nn { HYKaiTiS     } { HYKaiTiS.ttf      } }
    \__xdu_set_cjk_sans_font:n
      { \__xdu_select_font:nn { HYZhongHei   } { HYZhongHeiTiS.ttf } }
    \__xdu_set_cjk_mono_font:n
      { \__xdu_select_font:nn { HYFangSongS  } { HYFangSongS.ttf   } }
  }
\cs_new:Npn \__xdu_load_cjk_font_sinotype:
  {
    \__xdu_set_cjk_main_font:nn
      { \__xdu_select_font:nn { STSong     } { STSONG.TTF   } }
      { \__xdu_select_font:nn { STKaiti    } { STKAITI.TTF  } }
    \__xdu_set_cjk_sans_font:nn
      { \__xdu_select_font:nn { STXihei    } { STXIHEI.TTF  } }
      { \__xdu_select_font:nn { STHeiti    } { STHeiti.ttf  } }
    \__xdu_set_cjk_mono_font:n
      { \__xdu_select_font:nn { STFangsong } { STFANGSO.TTF } }
  }
\cs_new:Npn \__xdu_load_cjk_font_fandol:
  {
    \__xdu_set_cjk_main_font:nnn
      { FandolSong-Regular.otf }
      { FandolSong-Bold.otf    }
      { FandolKai-Regular.otf  }
    \__xdu_set_cjk_sans_font:nn
      { FandolHei-Regular.otf  }
      { FandolHei-Bold.otf     }
    \__xdu_set_cjk_mono_font:n
      { FandolFang-Regular.otf }
  }
\cs_new:Npn \__xdu_load_cjk_font_none: { }
\cs_new:Npn \__xdu_set_latin_font:nnn #1#2#3
  {
    BoldFont        = { #1 },
    SlantedFont     = { #2 },
    BoldSlantedFont = { #3 },
    ItalicFont      = { #2 },
    BoldItalicFont  = { #3 }
  }
\cs_new:Npn \__xdu_set_latin_sans_scale: { }
\cs_new:Npn \__xdu_set_latin_mono_scale: { }
\ctex_at_end_preamble:n
  {
    \tl_if_eq:NnTF \l__xdu_latin_sans_scale_tl { upper }
      { \cs_set:Npn \__xdu_set_latin_sans_scale: { Scale = MatchUppercase , } }
      {
        \tl_if_eq:NnT \l__xdu_latin_sans_scale_tl { lower }
          { \cs_set:Npn \__xdu_set_latin_sans_scale: { Scale = MatchLowercase , } }
      }
    \tl_if_eq:NnTF \l__xdu_latin_mono_scale_tl { upper }
      { \cs_set:Npn \__xdu_set_latin_mono_scale: { Scale = MatchUppercase , } }
      {
        \tl_if_eq:NnT \l__xdu_latin_mono_scale_tl { lower }
          { \cs_set:Npn \__xdu_set_latin_mono_scale: { Scale = MatchLowercase , } }
      }
  }
\cs_new:Npn \__xdu_off_latin_ligatures:
  { Ligatures = CommonOff , }
\cs_new:Npn \__xdu_set_latin_main_font:nnnnn #1#2#3#4#5
  {
    \str_if_eq:NNTF { \l__xdu_font_type_tl } { font }
      { \setmainfont { #1 } }
      {
        \setmainfont { #2 }
          [
            \__xdu_font_path:
            \__xdu_set_latin_font:nnn { #3 } { #4 } { #5 }
          ]
      }
  }
\cs_new:Npn \__xdu_set_latin_sans_font:nnnnn #1#2#3#4#5
  {
    \str_if_eq:NNTF { \l__xdu_font_type_tl } { font }
      { \setsansfont { #1 } [ \__xdu_set_latin_sans_scale: ] }
      {
        \setsansfont { #2 }
          [
            \__xdu_font_path:
            \__xdu_set_latin_sans_scale:
            \__xdu_set_latin_font:nnn { #3 } { #4 } { #5 }
          ]
      }
  }
\cs_new:Npn \__xdu_set_latin_mono_font:nnnnn #1#2#3#4#5
  {
    \str_if_eq:NNTF { \l__xdu_font_type_tl } { font }
      { \setmonofont { #1 } [ \__xdu_set_latin_mono_scale: \__xdu_off_latin_ligatures: ] }
      {
        \setmonofont { #2 }
          [
            \__xdu_font_path:
            \__xdu_set_latin_mono_scale:
            \__xdu_off_latin_ligatures:
            \__xdu_set_latin_font:nnn { #3 } { #4 } { #5 }
          ]
      }
  }
\cs_new:Npn \__xdu_set_latin_main_font:nnnn #1#2#3#4
  {
    \setmainfont { #1 }
      [
        \__xdu_set_latin_font:nnn { #2 } { #3 } { #4 }
      ]
  }
\cs_new:Npn \__xdu_set_latin_sans_font:nnnn #1#2#3#4
  {
    \setsansfont { #1 }
      [
        \__xdu_set_latin_sans_scale:
        \__xdu_set_latin_font:nnn { #2 } { #3 } { #4 }
      ]
  }
\cs_new:Npn \__xdu_set_latin_mono_font:nnnn #1#2#3#4
  {
    \setmonofont { #1 }
      [
        \__xdu_set_latin_mono_scale:
        \__xdu_off_latin_ligatures:
        \__xdu_set_latin_font:nnn { #2 } { #3 } { #4 }
      ]
  }
\cs_new:Npn \__xdu_load_latin_font_tac:
  {
    \__xdu_set_latin_main_font:nnnnn
      { Times~New~Roman } { times.ttf   } { timesbd.ttf  } { timesi.ttf   } { timesbi.ttf  }
    \__xdu_set_latin_sans_font:nnnnn
      { Arial           } { arial.ttf   } { arialbd.ttf  } { ariali.ttf   } { arialbi.ttf  }
    \__xdu_set_latin_mono_font:nnnnn
      { Consolas        } { consola.ttf } { consolab.ttf } { consolai.ttf } { consolaz.ttf }
  }
\cs_new:Npn \__xdu_load_latin_font_tacn:
  {
    \__xdu_set_latin_main_font:nnnnn
      { Times~New~Roman } { times.ttf } { timesbd.ttf } { timesi.ttf } { timesbi.ttf }
    \__xdu_set_latin_sans_font:nnnnn
      { Arial           } { arial.ttf } { arialbd.ttf } { ariali.ttf } { arialbi.ttf }
    \__xdu_set_latin_mono_font:nnnnn
      { Courier~New     } { cour.ttf  } { courbd.ttf  } { couri.ttf  } { courbi.ttf  }
  }
\cs_new:Npn \__xdu_load_latin_font_tcc:
  {
    \__xdu_set_latin_main_font:nnnnn
      { Times~New~Roman }
      { times.ttf       }
      { timesbd.ttf     }
      { timesi.ttf      }
      { timesbi.ttf     }
    \__xdu_set_latin_sans_font:nnnn
      { cmunss.otf      }
      { cmunsx.otf      }
      { cmunsi.otf      }
      { cmunso.otf      }
    \__xdu_set_latin_mono_font:nnnn
      { cmuntt.otf      }
      { cmuntb.otf      }
      { cmunit.otf      }
      { cmuntx.otf      }
  }
\cs_new:Npn \__xdu_load_latin_font_thcs:
  {
    \__xdu_set_latin_main_font:nnnnn
      { Times~New~Roman            }
      { times.ttf                  }
      { timesbd.ttf                }
      { timesi.ttf                 }
      { timesbi.ttf                }
    \__xdu_set_latin_sans_font:nnnnn
      { Helvetica                  }
      { Helvetica.ttf              }
      { Helvetica~Bold.ttf         }
      { Helvetica~Oblique.ttf      }
      { Helvetica~Bold~Oblique.ttf }
    \__xdu_set_latin_mono_font:nnnnn
      { Courier~Std                }
      { CourierStd.otf             }
      { CourierStd-Bold.otf        }
      { CourierStd-Oblique.otf     }
      { CourierStd-BoldOblique.otf }
  }
\cs_new:Npn \__xdu_load_latin_font_tll:
  {
    \__xdu_set_latin_main_font:nnnnn
      { Times~New~Roman      }
      { times.ttf            }
      { timesbd.ttf          }
      { timesi.ttf           }
      { timesbi.ttf          }
    \__xdu_set_latin_sans_font:nnnn
      { LinBiolinum_R.otf    }
      { LinBiolinum_RB.otf   }
      { LinBiolinum_RI.otf   }
      { LinBiolinum_RBO.otf  }
    \__xdu_set_latin_mono_font:nnnn
      { LinLibertine_M.otf   }
      { LinLibertine_MB.otf  }
      { LinLibertine_MO.otf  }
      { LinLibertine_MBO.otf }
  }
\cs_new:Npn \__xdu_load_latin_font_gyre:
  {
    \__xdu_set_latin_main_font:nnnn
      { texgyretermes-regular.otf    }
      { texgyretermes-bold.otf       }
      { texgyretermes-italic.otf     }
      { texgyretermes-bolditalic.otf }
    \__xdu_set_latin_sans_font:nnnn
      { texgyreheros-regular.otf     }
      { texgyreheros-bold.otf        }
      { texgyreheros-italic.otf      }
      { texgyreheros-bolditalic.otf  }
    \__xdu_set_latin_mono_font:nnnn
      { texgyrecursor-regular.otf    }
      { texgyrecursor-bold.otf       }
      { texgyrecursor-italic.otf     }
      { texgyrecursor-bolditalic.otf }
  }
\cs_new:Npn \__xdu_load_latin_font_none: { }
\cs_new:Npn \__xdu_load_unicode_math_pkg:
  {
    \PassOptionsToPackage { \l__xdu_unicode_math_tl } { unicode-math }
    \RequirePackage  { unicode-math }
    \setoperatorfont { \symup       }
    \hypersetup      { psdextra     }
  }
\cs_new:Npn \__xdu_load_math_font_cambria:
  {
    \__xdu_load_unicode_math_pkg:
    \str_if_eq:NNTF { \l__xdu_font_type_tl } { font }
      { \setmathfont { Cambria~Math } }
      { \setmathfont { cambria.ttc } [ Path = \l__xdu_font_path_tl/, FontIndex = 1 ] }
  }
\cs_new:Npn \__xdu_define_math_font:nn #1#2
  {
    \cs_new:cpn { __xdu_load_math_font_ #1 : }
      {
        \__xdu_load_unicode_math_pkg:
        \setmathfont { #2 }
      }
  }
\clist_map_inline:nn
  {
    { asana          } { Asana-Math.otf             },
    { concrete       } { Concrete-Math.otf          },
    { erewhon        } { Erewhon-Math.otf           },
    { euler          } { Euler-Math.otf             },
    { fira           } { FiraMath-Regular.otf       },
    { garamond       } { Garamond-Math.otf          },
    { gfsneohellenic } { GFSNeohellenicMath.otf     },
    { kp             } { KpMath-Regular.otf         },
    { libertinus     } { LibertinusMath-Regular.otf },
    { lm             } { latinmodern-math.otf       },
    { newcm          } { NewCMMath-Regular.otf      },
    { stix           } { STIXMath-Regular.otf       },
    { stix2          } { STIXTwoMath-Regular.otf    },
    { xcharter       } { XCharter-Math.otf          },
    { xits           } { XITSMath-Regular.otf       },
    { bonum          } { texgyrebonum-math.otf      },
    { dejavu         } { texgyredejavu-math.otf     },
    { pagella        } { texgyrepagella-math.otf    },
    { schola         } { texgyreschola-math.otf     },
    { termes         } { texgyretermes-math.otf     }
  }
  { \__xdu_define_math_font:nn #1 }
\cs_new:Npn \__xdu_load_math_font_cm: { }
\cs_new:Npn \__xdu_load_math_font_none: { }
\cs_new:Npn \__xdu_load_font:
  {
    \use:c { __xdu_load_cjk_font_   \l__xdu_cjk_font_tl   : }
    \use:c { __xdu_load_latin_font_ \l__xdu_latin_font_tl : }
    \use:c { __xdu_load_math_font_  \l__xdu_math_font_tl  : }
  }
\ctex_at_end_preamble:n { \__xdu_load_font: }
\tl_new:N \l__xdu_title_tl
\tl_new:N \l__xdu_title_i_tl
\tl_new:N \l__xdu_title_ii_tl
\str_new:N \l__xdu_dept_str
\str_new:N \l__xdu_major_str
\str_new:N \l__xdu_author_str
\clist_new:N \l__xdu_supv_clist
\str_new:N \l__xdu_supv_ent_str
\str_new:N \l__xdu_student_id_str
\tl_new:N \l__xdu_abstract_zh_tl
\tl_new:N \l__xdu_abstract_en_tl
\clist_new:N \l__xdu_keywords_zh_clist
\clist_new:N \l__xdu_keywords_en_clist
\clist_new:N \l__xdu_bib_file_clist
\clist_new:N \l__xdu_appendix_clist
\tl_new:N \l__xdu_ack_tl
\keys_define:nn { xdu / info }
  {
    title .tl_set:N = \l__xdu_title_tl,
    department .tl_set:N = \l__xdu_dept_str,
    major .tl_set:N = \l__xdu_major_str,
    author .tl_set:N = \l__xdu_author_str,
    supervisor .clist_set:N = \l__xdu_supv_clist,
    supv-ent .tl_set:N = \l__xdu_supv_ent_str,
    supervisor-enterprise .tl_set:N = \l__xdu_supv_ent_str,
    student-id .tl_set:N = \l__xdu_student_id_str,
    abstract .tl_set:N = \l__xdu_abstract_zh_tl,
    abstract* .tl_set:N = \l__xdu_abstract_en_tl,
    keywords .clist_set:N = \l__xdu_keywords_zh_clist,
    keywords* .clist_set:N = \l__xdu_keywords_en_clist,
    bib-resource .clist_set:N = \l__xdu_bib_file_clist,
    appendix .clist_set:N = \l__xdu_appendix_clist,
    acknowledgements .tl_set:N = \l__xdu_ack_tl
  }
\keys_set:nn { xdu }
  {
    info / title                 = { },
    info / department            = { },
    info / major                 = { },
    info / author                = { },
    info / supervisor            = { },
    info / supv-ent              = { },
    info / supervisor-enterprise = { },
    info / student-id            = { },
    info / abstract              = { },
    info / abstract*             = { },
    info / keywords              = { },
    info / keywords*             = { },
    info / bib-resource          = { },
    info / appendix              = { },
    info / acknowledgements      = { }
  }
\str_new:N \l__xdu_supv_str
\str_new:N \l__xdu_supv_ii_str
\ctex_at_end_preamble:n
  {
    \str_set:Nx \l__xdu_supv_str    { \clist_item:Nn \l__xdu_supv_clist { 1 } }
    \str_set:Nx \l__xdu_supv_ii_str { \clist_item:Nn \l__xdu_supv_clist { 2 } }
  }
\str_new:N \l__xdu_supv_dept_str
\str_new:N \l__xdu_supv_sch_str
\str_new:N \l__xdu_class_id_str
\keys_define:nn { xdu / info }
  {
    supv-dept .tl_set:N = \l__xdu_supv_dept_str,
    supervisor-department .tl_set:N = \l__xdu_supv_dept_str,
    supv-school .tl_set:N = \l__xdu_supv_sch_str,
    supervisor-school .tl_set:N = \l__xdu_supv_sch_str,
    class-id .tl_set:N = \l__xdu_class_id_str
  }
\keys_set:nn { xdu }
  {
    info / supv-dept             = { },
    info / supervisor-department = { },
    info / supv-school           = { },
    info / supervisor-school     = { },
    info / class-id              = { }
  }
\cs_set:Npn \figurename { \__xdu_lang_switch:nn { 图 } { Figure } }
\cs_new_eq:NN \figname \figurename
\cs_set:Npn \tablename  { \__xdu_lang_switch:nn { 表 } { Table  } }
\cs_new_eq:NN \tabname \tablename
\bool_new:N \l__xdu_title_bold_math_bool
\bool_new:N \l__xdu_en_cjk_font_bool
\tl_new:N \l__xdu_lang_tl
\tl_new:N \l__xdu_bib_tool_tl
\tl_new:N \l__xdu_biblatex_option_tl
\clist_new:N \l__xdu_search_path_clist
\bool_new:N \l__xdu_fix_input_bool
\bool_new:N \l__xdu_fix_include_bool
\bool_new:N \l__xdu_fix_graphics_bool
\tl_new:N \l__xdu_ref_add_space_bool
\tl_new:N \l__xdu_cap_label_sep_tl
\tl_new:N \l__xdu_ft_cap_format_tl
\tl_new:N \l__xdu_alg_cap_format_tl
\tl_new:N \l__xdu_ft_cap_align_tl
\tl_new:N \l__xdu_alg_cap_align_tl
\bool_new:N \l__xdu_add_alg_rule_vspace_bool
\bool_new:N \l__xdu_tab_small_bool
\tl_new:N \l__xdu_figure_align_tl
\tl_new:N \l__xdu_table_align_tl
\bool_new:N \l__xdu_alg_small_cap_bool
\bool_new:N \l__xdu_alg_small_bool
\clist_new:N \l__xdu_before_skip_clist
\clist_new:N \l__xdu_after_skip_clist
\tl_new:N \l__xdu_chap_tl
\tl_new:N \l__xdu_sec_tl
\tl_new:N \l__xdu_subsec_tl
\tl_new:N \l__xdu_subsubsec_tl
\tl_new:N \l__xdu_para_tl
\tl_new:N \l__xdu_subpara_tl
\bool_new:N \l__xdu_sym_mgn_bool
\tl_new:N \l__xdu_page_v_align_tl
\keys_define:nn { xdu / style }
  {
    title-bold-math .bool_set:N = \l__xdu_title_bold_math_bool,
    en-cjk-font .bool_set:N = \l__xdu_en_cjk_font_bool,
    language .choices:nn = { zh, en }
      { \tl_set_eq:NN \l__xdu_lang_tl \l_keys_choice_tl },
    bib-backend .choices:nn = { bibtex, biblatex }
      { \tl_set_eq:NN \l__xdu_bib_tool_tl \l_keys_choice_tl },
    biblatex-option .tl_set:N = \l__xdu_biblatex_option_tl,
    file-search-path .clist_set:N = \l__xdu_search_path_clist,
    fix-input .bool_set:N = \l__xdu_fix_input_bool,
    fix-include .bool_set:N = \l__xdu_fix_include_bool,
    fix-includegraphics .bool_set:N = \l__xdu_fix_graphics_bool,
    ref-add-space .bool_set:N = \l__xdu_ref_add_space_bool,
    caption-label-sep .tl_set:N = \l__xdu_cap_label_sep_tl,
    ft-caption-format .choices:nn = { plain, hang }
      { \tl_set_eq:NN \l__xdu_ft_cap_format_tl \l_keys_choice_tl },
    alg-caption-format .choices:nn = { plain, hang }
      { \tl_set_eq:NN \l__xdu_alg_cap_format_tl \l_keys_choice_tl },
    ft-caption-align .choices:nn = { left, centering, centering-left }
      { \tl_set_eq:NN \l__xdu_ft_cap_align_tl \l_keys_choice_tl },
    alg-caption-align .choices:nn = { left, centering, centering-left }
      { \tl_set_eq:NN \l__xdu_alg_cap_align_tl \l_keys_choice_tl },
    add-alg-rule-vspace .bool_set:N = \l__xdu_add_alg_rule_vspace_bool,
    table-small-font .bool_set:N = \l__xdu_tab_small_bool,
    figure-align .choices:nn = { left, centering, right }
      { \tl_set_eq:NN \l__xdu_figure_align_tl \l_keys_choice_tl },
    table-align .choices:nn = { left, centering, right }
      { \tl_set_eq:NN \l__xdu_table_align_tl \l_keys_choice_tl },
    alg-small-caption .bool_set:N = \l__xdu_alg_small_cap_bool,
    algorithm-small-caption .bool_set:N = \l__xdu_alg_small_cap_bool,
    alg-small-font .bool_set:N = \l__xdu_alg_small_bool,
    algorithm-small-font .bool_set:N = \l__xdu_alg_small_bool,
    before-skip .clist_set:N = \l__xdu_before_skip_clist,
    after-skip .clist_set:N = \l__xdu_after_skip_clist,
    chap-zihao .tl_set:N = \l__xdu_chap_tl,
    sec-zihao .tl_set:N = \l__xdu_sec_tl,
    subsec-zihao .tl_set:N = \l__xdu_subsec_tl,
    subsubsec-zihao .tl_set:N = \l__xdu_subsubsec_tl,
    para-zihao .tl_set:N = \l__xdu_para_tl,
    subpara-zihao .tl_set:N = \l__xdu_subpara_tl,
    symmetric-margin .bool_set:N = \l__xdu_sym_mgn_bool,
    page-vertical-align .tl_set:N = \l__xdu_page_v_align_tl
  }
\keys_set:nn { xdu }
  {
    style / title-bold-math         = false,
    style / en-cjk-font             = false,
    style / language                = zh,
    style / bib-backend             = biblatex,
    style / biblatex-option         = { },
    style / file-search-path        = { },
    style / fix-input               = false,
    style / fix-include             = false,
    style / fix-includegraphics     = false,
    style / ref-add-space           = false,
    style / caption-label-sep       = 0.75em,
    style / ft-caption-format       = hang,
    style / alg-caption-format      = hang,
    style / ft-caption-align        = centering-left,
    style / alg-caption-align       = left,
    style / add-alg-rule-vspace     = false,
    style / table-small-font        = true,
    style / figure-align            = centering,
    style / table-align             = centering,
    style / alg-small-caption       = true,
    style / algorithm-small-caption = true,
    style / alg-small-font          = true,
    style / algorithm-small-font    = true,
    style / before-skip             = { 24pt, 18pt, 12pt, 12pt, 12pt, 12pt },
    style / after-skip              = { 18pt, 12pt, 6pt, 6pt, 6pt, 6pt },
    style / symmetric-margin        = false,
    style / page-vertical-align     = 顶部对齐
  }
\cs_new:Npn \__xdu_bold_math: { }
\ctex_at_end_preamble:n
  {
    \bool_if:NT \l__xdu_title_bold_math_bool
      {
        \tl_if_eq:NnT \l__xdu_math_font_tl { cm }
          { \cs_set_eq:NN \__xdu_bold_math: \boldmath }
      }
  }
\NewDocumentCommand \xdusetup { m }
  { \keys_set:nn { xdu } { #1 } }
\keys_define:nn { xdu }
  {
    style .meta:nn = { xdu / style } { #1 },
    info  .meta:nn = { xdu / info  } { #1 }
  }
\ProcessKeysOptions { xdu / style }
\cs_new:Npn \__xdu_lang_switch:nn #1#2
  {
    \str_if_eq:NNTF { \l__xdu_lang_tl } { zh }
      { #1 }
      { #2 }
  }
\cs_new:Npn \__xdu_rm_family:
  { \bool_if:NTF \l__xdu_en_cjk_font_bool { \CJKfamily+ { rm } } { \rmfamily } }
\cs_new:Npn \__xdu_sf_family:
  { \bool_if:NTF \l__xdu_en_cjk_font_bool { \CJKfamily+ { sf } } { \sffamily } }
\cs_new:Npn \__xdu_tt_family:
  { \bool_if:NTF \l__xdu_en_cjk_font_bool { \CJKfamily+ { tt } } { \ttfamily } }
\ctex_at_end_preamble:n
  {
    \tl_new:N \l__xdu_pure_title_tl
    \tl_set_eq:NN \l__xdu_pure_title_tl \l__xdu_title_tl
    \tl_remove_all:Nn \l__xdu_pure_title_tl { \\ }
  }
\cs_new_protected:Npn \__xdu_split_title:Nn #1#2
  {
    \seq_new:N \l__xdu_title_seq
    \tl_if_in:nnTF { #2 } { \\ }
      {
        \seq_set_split:Nnn \l__xdu_title_seq { \\ } { #2 }
        \clist_set_from_seq:NN #1 \l__xdu_title_seq
      }
      { \clist_set:Nx #1 { #2 } }
  }
\cs_generate_variant:Nn \__xdu_split_title:Nn { NV }
\cs_new:Npn \__xdu_uline:n #1
  { \CJKunderline [ thickness = 0.5pt ] { #1 } }
\cs_new:Npn \__xdu_tl_set_if_empty:Nn #1#2
  { \tl_if_empty:NT #1 { \tl_set:Nn #1 { #2 } } }
\cs_new:Npn \__xdu_get_text_width:Nn #1#2
  {
    \box_clear_new:N \l__xdu_tmp_box
    \hbox_set:Nn \l__xdu_tmp_box { #2 }
    \dim_set:Nn #1 { \box_wd:N \l__xdu_tmp_box }
  }
\cs_generate_variant:Nn \__xdu_get_text_width:Nn { NV }
\cs_new:Npn \__xdu_add_bookmark:n #1
  {
    \cleardoublepage
    \currentpdfbookmark { #1 } { #1 }
  }
\cs_new:Npn \__xdu_add_toc:n #1
  {
    \cleardoublepage
    \phantomsection
    \addcontentsline { toc } { chapter } { #1 }
  }
\cs_new:Npn \__xdu_n_chapter_head:n #1
  {
    \__xdu_add_bookmark:n { #1 }
    \chapter*          { #1 }
    \markboth          { #1 } { }
  }
\cs_new:Npn \__xdu_n_chapter_head_ii:nn #1#2
  {
    \group_begin:
      \ctexset { chapter / format = { #2 } }
      \__xdu_n_chapter_head:n { #1 }
    \group_end:
  }
\cs_new:Npn \__xdu_n_chapter_head:nn #1#2
  {
    \__xdu_add_bookmark:n { #1 }
    \chapter*          { #2 }
    \markboth          { #1 } { }
  }
\cs_new:Npn \__xdu_n_chapter_head_ii:nnn #1#2#3
  {
    \group_begin:
      \ctexset { chapter / format = { #3 } }
      \__xdu_n_chapter_head:nn { #1 } { #2 }
    \group_end:
  }
\cs_new:Npn \__xdu_n_chapter_head_toc:n #1
  {
    \__xdu_add_toc:n { #1 }
    \chapter* { #1 }
    \markboth { #1 } { }
  }
\cs_new:Npn \__xdu_n_chapter_head_toc:nn #1#2
  {
    \__xdu_add_toc:n { #1 }
    \chapter* { #2 }
    \markboth { #1 } { }
  }
\cs_new:Npn \__xdu_n_chapter_head_toc_ii:nn #1#2
  {
    \group_begin:
      \ctexset { chapter / format = { #2 } }
      \__xdu_n_chapter_head_toc:n { #1 }
    \group_end:
  }
\cs_new:Npn \__xdu_typeout_keywords:nNn #1#2#3
  {
    \tl_clear_new:N \l__xdu_keywords_label_str
    \tl_set:Nn \l__xdu_keywords_label_tl { #1 }
    \dim_zero_new:N \l__xdu_keywords_label_dim
    \__xdu_get_text_width:NV \l__xdu_keywords_label_dim \l__xdu_keywords_label_tl
    \begin { list } { \l__xdu_keywords_label_tl }
      {
        \labelwidth  \l__xdu_keywords_label_dim
        \labelsep    \c_zero_dim
        \rightmargin \c_zero_dim
        \leftmargin  \l__xdu_keywords_label_dim
      }
      \item \clist_use:Nnnn #2 { #3 } { #3 } { #3 }
    \end { list }
  }
\dim_new:N \l__xdu_str_dim
\box_new:N \l__xdu_str_box
\cs_new:Npn \__xdu_str_max_dim:Nn #1#2
  {
    \hbox_set:Nn \l__xdu_str_box { #2 }
    \dim_set:Nn \l__xdu_str_dim { \box_wd:N \l__xdu_str_box }
    \dim_set:Nn #1  { \dim_max:nn { \l__xdu_str_dim } { #1 } }
  }
\NewDocumentCommand \noauxwrite { m }
  {
    \if@filesw
      \@fileswfalse
      #1
      \@fileswtrue
    \else
      #1
    \fi
  }
\newgeometry
  {
    top           = 3cm,
    bottom        = 2cm,
    inner         = 3cm,
    outer         = 2cm,
    bindingoffset = 1cm,
    head          = 2cm,
    foot          = 1cm
  }
\savegeometry { main }
\newgeometry
  {
    top    = 3cm,
    bottom = 2cm,
    inner  = 3cm,
    outer  = 3cm,
    head   = 2cm,
    foot   = 1cm
  }
\savegeometry { main-sym }
\newgeometry
  {
    top    = 2.5cm,
    bottom = 2cm,
    inner  = 3cm,
    outer  = 2cm
  }
\savegeometry { cover }
\cs_new:Npn \__xdu_load_main_geometry:
  {
    \bool_if:NTF \l__xdu_sym_mgn_bool
      { \loadgeometry { main-sym } }
      { \loadgeometry { main     } }
  }
\clist_map_inline:nn
  {
    { chinese  },
    { arabic   },
    { roman    },
    { Roman    },
    { alph     },
    { Alph     },
    { fnsymbol }
  }
  { \cs_new_eq:cc { __xdu _ #1 : } { #1 } }
\tl_set:Nn \chaptername { Chapter }
\tl_new:N \l__xdu_chaptername
\tl_set_eq:NN \l__xdu_chaptername \chaptername
\renewcommand { \chaptermark } [ 1 ]
  {
    \markboth
      {
        \__xdu_lang_switch:nn
          { \CTEXthechapter }
          { \l__xdu_chaptername \space \__xdu_Roman: { chapter } }
        \quad #1
      }
      { }
  }
\fancypagestyle { plain }
  {
    \pagestyle { fancy }
    \fancyhf { }
    \fancyhead [ CE ] { \__xdu_rm_family: \zihao { 5  } \l__xdu_pure_title_tl }
    \fancyhead [ CO ] { \__xdu_rm_family: \zihao { 5  } \leftmark            }
    \fancyhead [ LE ] { \__xdu_rm_family: \zihao { -5 } \thepage             }
    \fancyhead [ RO ] { \__xdu_rm_family: \zihao { -5 } \thepage             }
    \renewcommand { \headrulewidth } { 0.75pt }
  }
\ctex_at_end_preamble:n
  {
    \tl_if_eq:NnTF \l__xdu_page_v_align_tl { 顶部对齐 }
      { \raggedbottom }
      { \flushbottom  }
  }
\ctexset { secnumdepth=5 }
\ctexset
  {
    chapter       / name =
      {
        \__xdu_lang_switch:nn { 第 } { \l__xdu_chaptername \space },
        \__xdu_lang_switch:nn { 章 } { }
      },
    section       / name = { },
    subsection    / name = { },
    subsubsection / name = { },
    paragraph     / name = { },
    subparagraph  / name = { }
  }
\ctex_at_end_preamble:n
  {
    \__xdu_lang_switch:nn
      {
        \ctexset
          {
            chapter       / number = { \chinese { chapter } },
            section       / number = { \thesection          },
            subsection    / number = { \thesubsection       },
            subsubsection / number = { \thesubsubsection    },
            paragraph     / number = { \theparagraph        },
            subparagraph  / number = { \thesubparagraph     }
          }
      }
      {
        \ctexset
          {
            chapter       / number = { \Roman { chapter }           },
            section       / number = { \thesection                  },
            subsection    / number = { \thesubsection               },
            subsubsection / number = { ( \roman { subsubsection } ) },
            paragraph     / number = { ( \alph { paragraph } )      },
            subparagraph  / number = { ( \arabic { subparagraph } ) }
          }
      }
  }
\cs_new:Npn \__xdu_zh_t:nnn #1#2#3
  {
    \use:c { __xdu_ #1 _family : }
    \zihao { \use:c { l__xdu_ #2 _tl } }
    \str_if_eq:ccTF { #3 } { c }
      { \centering   }
      { \raggedright }
  }
\cs_new:Npn \__xdu_en_t:nn #1#2
  {
    \rmfamily
    \zihao { \use:c { l__xdu_ #1 _tl } }
    \bfseries \__xdu_bold_math:
    \str_if_eq:ccTF { #2 } { c }
      { \centering   }
      { \raggedright }
  }
\ctex_at_end_preamble:n
  {
    \__xdu_lang_switch:nn
      {
        \__xdu_tl_set_if_empty:Nn \l__xdu_chap_tl      { 3  }
        \__xdu_tl_set_if_empty:Nn \l__xdu_sec_tl       { 4  }
        \__xdu_tl_set_if_empty:Nn \l__xdu_subsec_tl    { -4 }
        \__xdu_tl_set_if_empty:Nn \l__xdu_subsubsec_tl { -4 }
        \__xdu_tl_set_if_empty:Nn \l__xdu_para_tl      { -4 }
        \__xdu_tl_set_if_empty:Nn \l__xdu_subpara_tl   { -4 }
        \ctexset
          {
            chapter       / format = { \__xdu_zh_t:nnn { sf } { chap      } { c } \__xdu_bold_math: },
            section       / format = { \__xdu_zh_t:nnn { rm } { sec       } { c } },
            subsection    / format = { \__xdu_zh_t:nnn { rm } { subsec    } { l } },
            subsubsection / format = { \__xdu_zh_t:nnn { rm } { subsubsec } { l } },
            paragraph     / format = { \__xdu_zh_t:nnn { rm } { para      } { l } },
            subparagraph  / format = { \__xdu_zh_t:nnn { rm } { subpara   } { l } }
          }
      }
      {
        \__xdu_tl_set_if_empty:Nn \l__xdu_chap_tl      { 3  }
        \__xdu_tl_set_if_empty:Nn \l__xdu_sec_tl       { 4  }
        \__xdu_tl_set_if_empty:Nn \l__xdu_subsec_tl    { -4 }
        \__xdu_tl_set_if_empty:Nn \l__xdu_subsubsec_tl { -4 }
        \__xdu_tl_set_if_empty:Nn \l__xdu_para_tl      { -4 }
        \__xdu_tl_set_if_empty:Nn \l__xdu_subpara_tl   { -4 }
        \ctexset
          {
            chapter       / format = { \__xdu_en_t:nn { chap      } { c } },
            section       / format = { \__xdu_en_t:nn { sec       } { l } },
            subsection    / format = { \__xdu_en_t:nn { subsec    } { l } },
            subsubsection / format = { \__xdu_en_t:nn { subsubsec } { l } },
            paragraph     / format = { \__xdu_en_t:nn { para      } { l } },
            subparagraph  / format = { \__xdu_en_t:nn { subpara   } { l } }
          }
      }
  }
\ctexset
  {
    chapter       / fixskip    = true,
    section       / fixskip    = true,
    subsection    / fixskip    = true,
    subsubsection / fixskip    = true,
    paragraph     / fixskip    = true,
    subparagraph  / fixskip    = true,
    chapter       / beforeskip = { \clist_item:Nn \l__xdu_before_skip_clist { 1 } },
    section       / beforeskip = { \clist_item:Nn \l__xdu_before_skip_clist { 2 } },
    subsection    / beforeskip = { \clist_item:Nn \l__xdu_before_skip_clist { 3 } },
    subsubsection / beforeskip = { \clist_item:Nn \l__xdu_before_skip_clist { 4 } },
    paragraph     / beforeskip = { \clist_item:Nn \l__xdu_before_skip_clist { 5 } },
    subparagraph  / beforeskip = { \clist_item:Nn \l__xdu_before_skip_clist { 6 } },
    chapter       / afterskip  = { \clist_item:Nn \l__xdu_after_skip_clist  { 1 } },
    section       / afterskip  = { \clist_item:Nn \l__xdu_after_skip_clist  { 2 } },
    subsection    / afterskip  = { \clist_item:Nn \l__xdu_after_skip_clist  { 3 } },
    subsubsection / afterskip  = { \clist_item:Nn \l__xdu_after_skip_clist  { 4 } },
    paragraph     / afterskip  = { \clist_item:Nn \l__xdu_after_skip_clist  { 5 } },
    subparagraph  / afterskip  = { \clist_item:Nn \l__xdu_after_skip_clist  { 6 } }
  }
\PassOptionsToPackage { titles } { tocloft }
\RequirePackage { tocloft }
\cs_set:Npn \cftchapleader { \bfseries \cftdotfill { \cftdotsep } }
\dim_set_eq:NN \cftbeforechapskip \cftbeforesecskip
\clist_map_inline:nn
  {
    \cftchapfont,
    \cftchappagefont
  }
  { \renewcommand { #1 } { \__xdu_rm_family: \zihao { -4 } \bfseries \__xdu_bold_math: } }
\clist_map_inline:nn
  {
    \cftsecfont,
    \cftsubsecfont,
    \cftsubsubsecfont,
    \cftparafont,
    \cftsubparafont,
    \cftsecpagefont,
    \cftsubsecpagefont,
    \cftsubsubsecpagefont,
    \cftparapagefont,
    \cftsubparapagefont
  }
  { \renewcommand { #1 } { \__xdu_rm_family: \zihao { -4 } } }
\ctex_at_end_preamble:n
  {
    \seq_if_empty:NF \l__xdu_search_path_clist
      {
        \clist_map_inline:Nn \l__xdu_search_path_clist
          { \seq_put_right:Nn \l_file_search_path_seq { #1 } }
      }
    \bool_if:NT \l__xdu_fix_input_bool
      {
        \cs_new_eq:NN \__xdu_org_input:n \input
        \RenewDocumentCommand { \input } { m }
          { \__xdu_org_input:n { ./ #1 } }
      }
    \bool_if:NT \l__xdu_fix_include_bool
      {
        \cs_new_eq:NN \__xdu_org_include:n \include
        \RenewDocumentCommand { \include } { m }
          { \__xdu_org_include:n { ./ #1 } }
      }
    \bool_if:NT \l__xdu_fix_graphics_bool
      {
        \cs_new_eq:NN \__xdu_org_includegraphics:n \includegraphics
        \RenewDocumentCommand { \includegraphics } { o m }
          {
            \IfNoValueTF { #1 }
              { \__xdu_org_includegraphics:n        { ./ #2 } }
              { \__xdu_org_includegraphics:n [ #1 ] { ./ #2 } }
          }
      }
  }
\renewcommand { \theequation } { \thechapter - \arabic { equation } }
\cs_set:Npn \topfraction       { .8 }
\cs_set:Npn \floatpagefraction { .8 }
\ctex_at_end_preamble:n
  {
    \clist_map_inline:nn
      {
        { \algorithmname   },
        { \ALG@name        },
        { \algorithmcfname }
      }
      { \cs_set:Npn #1 { \__xdu_lang_switch:nn { 算法 } { Algorithm } } }
  }
\PassOptionsToPackage { chapter } { algorithm }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { algorithm }
      {
        \cs_if_exist:NT \thealgorithm
          {
            \floatplacement { algorithm } { tbp }
            \cs_set:Npn \thealgorithm { \thechapter . \arabic { algorithm } }
            \bool_if:NT \l__xdu_alg_small_bool
              {
                \renewenvironment { algorithm }
                  {
                    \@nameuse { fst@algorithm }
                    \@float@setevery { algorithm }
                    \ctex_gadd_ltxhook:nn
                      { cmd/@floatboxreset/after }
                      { \zihao { 5 } }
                    \@float { algorithm }
                  }
                  { \float@end }
              }
          }
      }
      { }
  }
\PassOptionsToPackage { algochapter } { algorithm2e }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { algorithm2e }
      {
        \cs_if_exist:NT \thealgocf
          {
            \cs_set:Npn \thealgocf { \thechapter . \arabic { algocf } }
            \renewenvironment { \algocf@envname } [ 1 ] [ tbp ]
              {
                \setboolean { algocf@algostar } { false }
                \setboolean { algocf@procenvironment } { false }
                \gdef \algocfautorefname { \algorithmautorefname }
                \begin { algocf@algorithm } [ #1 ] \ignorespaces
              }
              { \end { algocf@algorithm } \ignorespacesafterend }
            \bool_if:NT \l__xdu_alg_small_bool
              { \SetAlFnt { \zihao { 5 } } }
          }
      }
      { }
  }
\PassOptionsToPackage { ruled } { caption }
\RequirePackage { caption }
\DeclareCaptionLabelSeparator { customskip } { \hskip \l__xdu_cap_label_sep_tl }
\DeclareCaptionFont { customfont   } { \__xdu_rm_family: \zihao { 5 } }
\captionsetup
  {
    strut    = off,
    labelsep = customskip,
    font     = customfont
  }
\captionsetup [ subfigure ] { strut = on, skip = 0pt }
\captionsetup [ subtable  ] { strut = on, skip = 0pt }
\dim_set_eq:NN \intextsep \abovecaptionskip
\ctex_at_end_preamble:n
  {
    \tl_if_eq:NnTF \l__xdu_ft_cap_format_tl { hang }
      { \captionsetup { format = hang  } }
      { \captionsetup { format = plain } }
    \tl_if_eq:NnTF \l__xdu_ft_cap_align_tl { left }
      { \captionsetup { singlelinecheck = false, justification = justified } }
      {
        \tl_if_eq:NnTF \l__xdu_ft_cap_align_tl { centering }
          { \captionsetup { singlelinecheck = false, justification = centerlast } }
          { \captionsetup { singlelinecheck = true, justification = justified   } }
      }
  }
\DeclareCaptionFont { algcustomfont }
  {
    \__xdu_rm_family:
    \bool_if:NTF \l__xdu_alg_small_cap_bool
      { \zihao { 5  } }
      { \zihao { -4 } }
  }
\captionsetup* [ algorithm ]
  {
    labelsep  = customskip,
    labelfont = algcustomfont,
    font      = algcustomfont
  }
\ctex_at_end_preamble:n
  {
    \tl_if_eq:NnTF \l__xdu_alg_cap_format_tl { hang }
      { \captionsetup* [ algorithm ] { format = hang  } }
      { \captionsetup* [ algorithm ] { format = plain } }
    \captionsetup* [ ruled ] { strut = off }
    \tl_if_eq:NnTF \l__xdu_alg_cap_align_tl { left }
      {
        \captionsetup* [ algorithm ]
          { singlelinecheck = false, justification = justified }
      }
      {
        \tl_if_eq:NnTF \l__xdu_alg_cap_align_tl { centering }
          {
            \captionsetup* [ algorithm ]
              { singlelinecheck = false, justification = centerlast }
          }
          {
            \captionsetup* [ ruled     ] { singlelinecheck = true    }
            \captionsetup* [ algorithm ] { justification = justified }
          }
      }
  }
\ctex_at_end_preamble:n
  {
    \bool_if:NT \l__xdu_add_alg_rule_vspace_bool
      {
        \@ifpackageloaded { algorithm }
          {
            \cs_set:Npn \fs@ruled
              {
                \cs_set_eq:NN \@fs@capt \floatc@plain
                \cs_set:Npn   \@fs@pre  { \hrule height .8pt depth 0pt \kern 5pt }
                \cs_set:Npn   \@fs@post { \kern 5pt \hrule \relax                }
                \cs_set:Npn   \@fs@mid  { \kern 5pt \hrule \kern 5pt             }
                \cs_set_eq:NN \@fs@iftopcapt \iftrue
              }
          }
          { }
      }
  }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { algorithm2e }
      {
        \SetAlgoCaptionSeparator { \hbox_to_wd:nn { \l__xdu_cap_label_sep_tl } { } }
        \bool_if:NTF \l__xdu_alg_small_cap_bool
          {
            \SetAlCapNameFnt         { \__xdu_rm_family: \zihao { 5  } }
            \SetAlCapFnt             { \__xdu_rm_family: \zihao { 5  } }
          }
          {
            \SetAlCapNameFnt         { \__xdu_rm_family: \zihao { -4 } }
            \SetAlCapFnt             { \__xdu_rm_family: \zihao { -4 } }
          }
        \SetAlCapSty { }
        \RenewDocumentCommand { \algocf@makecaption } { mm }
          {
            \box_clear_new:N \l__xdu_algiie_capt_box
            \hbox_set:Nn \l__xdu_algiie_capt_box
              { \AlCapFnt #1 \algocf@capseparator \AlCapNameFnt #2 }
            \dim_compare:nNnTF { \box_wd:N \l__xdu_algiie_capt_box } > { \hsize }
              {
                \tl_if_eq:NnTF \l__xdu_alg_cap_format_tl { hang }
                  {
                    \tl_if_eq:NnTF \l__xdu_alg_cap_align_tl { centering }
                      {
                        \makebox { \AlCapFnt #1 \algocf@capseparator }
                        \makebox
                          {
                            \parbox [ t ] { \hsize }
                              { \centering \AlCapNameFnt #2 }
                          }
                      }
                      {
                        \makebox { \AlCapFnt #1 \algocf@capseparator }
                        \makebox { \parbox [ t ] { \hsize } { \AlCapNameFnt #2 } }
                      }
                  }
                  {
                    \tl_if_eq:NnTF \l__xdu_alg_cap_align_tl { centering }
                      {
                        \parbox { \columnwidth }
                          { \centering \AlCapFnt #1 \algocf@capseparator \AlCapNameFnt #2 }
                      }
                      {
                        \parbox { \columnwidth }
                          { \AlCapFnt #1 \algocf@capseparator \AlCapNameFnt #2 }
                      }
                  }
              }
              {
                \tl_if_eq:NnTF \l__xdu_alg_cap_align_tl { left }
                  {
                    \parbox { \columnwidth }
                      { \AlCapFnt #1 \algocf@capseparator \AlCapNameFnt #2 }
                  }
                  {
                    \parbox { \columnwidth }
                      { \centering \AlCapFnt #1 \algocf@capseparator \AlCapNameFnt #2 }
                  }
              }
          }
        \RenewDocumentCommand { \algocf@makecaption@ruled } { mm }
          { \global \sbox \algocf@capbox { \algocf@makecaption { #1 } { #2 } } }
        \RenewDocumentCommand { \algocf@makecaption@boxed } { mm }
          { \global \sbox \algocf@capbox { \algocf@makecaption { #1 } { #2 } } }
      }
      { }
  }
\ctex_at_end_preamble:n
  {
    \bool_if:NT \l__xdu_add_alg_rule_vspace_bool
      {
        \@ifpackageloaded { algorithm2e }
          {
            \dim_set:Nn \interspacetitleruled { 5pt }
            \dim_set:Nn \interspacealgoruled  { 5pt }
          }
          { }
      }
  }
\cs_new:Npn \__xdu_tblr_caption_box:n #1
  { \makebox [ \tablewidth ] { \parbox { \columnwidth } { #1 } } }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { tabularray }
      {
        \SetTblrOuter [ tblr, longtblr, talltblr ]
          { presep = \belowcaptionskip + \intextsep, headsep = \abovecaptionskip }
        \SetTblrStyle { head } { font = \__xdu_rm_family: \zihao { 5 } }
        \DefTblrTemplate { caption-sep } { default }
          { \hskip \l__xdu_cap_label_sep_tl }
        \tl_if_eq:NnTF \l__xdu_cap_format_tl { hang }
          {
            \DefTblrTemplate { firsthead } { default }
              { \__xdu_tblr_caption_box:n { \UseTblrTemplate { caption  } { default } } }
            \DefTblrTemplate { middlehead, lasthead } { default }
              { \__xdu_tblr_caption_box:n { \UseTblrTemplate { capcont  } { default } } }
          }
          {
            \DefTblrTemplate { firsthead } { default }
              { \__xdu_tblr_caption_box:n { \UseTblrTemplate { caption  } { plain } } }
            \DefTblrTemplate { middlehead, lasthead } { default }
              { \__xdu_tblr_caption_box:n { \UseTblrTemplate { capcont  } { plain } } }
          }
        \DefTblrTemplate { firstfoot, middlefoot } { default }
          { \__xdu_tblr_caption_box:n { \UseTblrTemplate { contfoot } { default } } }
        \DefTblrTemplate { lastfoot } { default }
          {
            \__xdu_tblr_caption_box:n
              {
                \UseTblrTemplate { note   } { default }
                \UseTblrTemplate { remark } { default }
              }
          }
        \DefTblrTemplate { conthead-text } { default }
          { \__xdu_lang_switch:nn { （续表） } { (Continued) } }
        \DefTblrTemplate { contfoot-text } { default }
          { \__xdu_lang_switch:nn { 接下页 } { Continued~on~next~page } }
      }
      { }
  }
\ctex_at_end_preamble:n
  {
    \tl_if_eq:NnTF \l__xdu_figure_align_tl { left }
      {
          \AtBeginEnvironment { figure }
            { \g@addto@macro { \@floatboxreset } { \raggedright } }
      }
      {
        \tl_if_eq:NnTF \l__xdu_figure_align_tl { centering }
          {
            \AtBeginEnvironment { figure }
              { \g@addto@macro { \@floatboxreset } { \centering } }
          }
          {
            \AtBeginEnvironment { figure }
              { \g@addto@macro { \@floatboxreset } { \raggedleft } }
          }
      }
  }
\PassOptionsToPackage { font = small } { subfig }
\captionsetup* [ sub ] { font = customfont }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { subfig }
      { \captionsetup [ subfloat ] { subrefformat = parens } }
      { }
  }
\PassOptionsToPackage { labelformat = simple } { subcaption }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { subcaption }
      {
        \cs_set:Npn \thesubfigure { ( \alph { subfigure } ) }
        \cs_set:Npn \thesubtable  { ( \alph { subtable  } ) }
      }
      { }
  }
\ctex_at_end_preamble:n
  {
    \tl_if_eq:NnTF \l__xdu_table_align_tl { left }
      {
          \AtBeginEnvironment { table }
            { \g@addto@macro { \@floatboxreset } { \raggedright } }
      }
      {
        \tl_if_eq:NnTF \l__xdu_table_align_tl { centering }
          {
            \AtBeginEnvironment { table }
              { \g@addto@macro { \@floatboxreset } { \centering } }
          }
          {
            \AtBeginEnvironment { table }
              { \g@addto@macro { \@floatboxreset } { \raggedleft } }
          }
      }
  }
\ctex_at_end_preamble:n
  {
    \bool_if:NT \l__xdu_tab_small_bool
      {
        \AtBeginEnvironment { table }
          { \g@addto@macro { \@floatboxreset } { \small } }
      }
  }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { longtable }
      {
        \bool_if:NT \l__xdu_tab_small_bool
          {
            \ctex_gadd_ltxhook:nn
              { env/longtable/begin }
              { \small }
          }
      }
      { }
  }
\ctex_at_end_preamble:n
  {
    \@ifpackageloaded { tabularray }
      {
        \bool_if:NT \l__xdu_tab_small_bool
          {
            \ctex_gadd_ltxhook:nn
              { env/tblr/begin }
              { \small }
            \ctex_gadd_ltxhook:nn
              { env/longtblr/begin }
              { \small }
          }
      }
      { }
  }
\RequirePackage { hyperref }
\hypersetup
  {
    bookmarksnumbered,
    hidelinks
  }
\ctex_at_end_preamble:n
  {
    \hypersetup
      {
        pdftitle   = \l__xdu_pure_title_tl,
        pdfsubject = { 西安电子科技大学本科毕业设计论文 },
        pdfcreator = { XeLaTeX~with~xduugthesis~class~in~XDUTS },
        pdfauthor  = \l__xdu_author_str
      }
  }
\ctex_at_end_preamble:n
  {
    \bool_if:NT \l__xdu_ref_add_space_bool
      {
        \str_if_eq:NNT { \l__xdu_lang_tl } { zh }
          {
            \RequirePackage { xspace }
            \xspaceaddexceptions { 。？！，、；：“”‘’—….－-～·《》<>＿ }
            \cs_generate_variant:Nn \str_if_in:nnTF { xnTF }
            \ctex_after_end_preamble:n
              {
                \cs_set_eq:NN \__xdu_trad_ref:n \ref
                \cs_set:Npn \ref #1
                  {
                    \str_if_in:xnTF { \__hyp_get_anchor:n { #1 } } { chapter }
                      {         \__xdu_trad_ref:n { #1 }         }
                      { \xspace \__xdu_trad_ref:n { #1 } \xspace }
                  }
                \cs_set_eq:NN \__xdu_trad_page_ref:n \pageref
                \cs_set:Npn \pageref #1
                  { \xspace \__xdu_trad_page_ref:n { #1 } \xspace }
              }
          }
      }
  }
\cs_new_protected:Npn \__xdu_begin_document:n #1
  { \ctex_gadd_ltxhook:nn { env/document/begin } { #1 } }
\PassOptionsToPackage { sort&compress       } { gbt7714  }
\PassOptionsToPackage { style = gb7714-2015 } { biblatex }
\__xdu_begin_document:n
  {
    \tl_if_eq:NnTF \l__xdu_bib_tool_tl { bibtex }
      {
        \RequirePackage { gbt7714 }
        \bibliographystyle { gbt7714-numerical }
        \cs_set:Npn \@biblabel #1 { \hfill [ #1 ] }
        \cs_set:Npn \bibsection { }
        \dim_set:Nn \bibsep { 0pt }
        \NewDocumentCommand \parencite { m }
          { \group_begin: \citestyle { numbers } \cite { #1 } \group_end: }
      }
      {
        \PassOptionsToPackage { \l__xdu_biblatex_option_tl } { biblatex }
        \RequirePackage { biblatex }
        \clist_map_inline:Nn \l__xdu_bib_file_clist { \addbibresource { #1 } }
        \defbibheading { bibliography } [ ] { }
        \dim_set:Nn \biblabelsep { 1ex }
        \dim_set:Nn \bibitemsep { 0pt }
        \cs_set_eq:NN \SlashFont \rmfamily
      }
    \cs_set:Npn \bibfont
      {
        \__xdu_rm_family:
        \zihao { 5 }
      }
  }
\cs_new:Npn \__xdu_appendix:
  {
    \cs_set:Npn \appendixname { \__xdu_lang_switch:nn { 附录 } { Appendix } }
    \tl_set_eq:NN \l__xdu_chaptername \appendixname
    \cs_set_eq:NN \__xdu_Roman: \__xdu_Alph:
    \appendix
    \renewcommand { \thefigure } { \thechapter \arabic { figure } }
    \renewcommand { \thetable  } { \thechapter \arabic { table  } }
    \cs_if_exist:NT \thealgorithm
      { \cs_set:Npn \thealgorithm { \thechapter \arabic { algorithm } } }
    \cs_if_exist:NT \thealgocf
      { \cs_set:Npn \thealgocf { \thechapter \arabic { algocf } } }
    \bool_if_exist:NTF \l__xdu_rm_appendix_bool
      {
        \bool_if:NF \l__xdu_rm_appendix_bool
          {
            \clist_map_inline:Nn \l__xdu_appendix_clist
              { \file_if_exist_input:n { ##1 } }
          }
      }
      {
        \clist_map_inline:Nn \l__xdu_appendix_clist
          { \file_if_exist_input:n { ##1 } }
      }
  }
\cs_new:Npn \__xdu_cover_i:nn #1#2
  {
    \vbox_to_ht:nn { 12pt }
      {
        \mode_leave_vertical:
        \hfill
        \hbox:n
          {
            \__xdu_rm_family: \zihao { -4 } \bfseries
            \hbox_to_wd:nn { 3em } { #1 }
            \skip_horizontal:n { 1em }
            \__xdu_uline:n { \hbox_to_wd:nn { 15ex } { \hfil #2 \hfil } }
            \skip_horizontal:n { 1.5cm }
          }
      }
  }
\cs_new:Npn \__xdu_cover_ii:nnn #1#2#3
  {
    \vbox_to_ht:nn { #1 }
      {
        \mode_leave_vertical:
        \hfil
        \file_if_exist:nT { xdulogo.pdf }
          {
            \str_if_eq:nnTF { #3 } { text }
              { \includegraphics [ page = 1, height = #2 ] { xdulogo.pdf } }
              { \includegraphics [ page = 2, height = #2 ] { xdulogo.pdf } }
          }
        \hfil
      }
  }
\cs_new:Npn \__xdu_cover_iii:nnnnn #1#2#3#4#5
  {
    \vbox_to_ht:nn { 42.5pt }
      {
        \vfill
        \mode_leave_vertical:
        \hfil
        \hbox:n
          {
            \__xdu_rm_family:
            \zihao { 3 }
            \hbox_to_wd:nn { #1 } { \bfseries #2 }
            \skip_horizontal:n { 1em }
            \zihao { -3 }
            \__xdu_uline:n
              {
                \hbox_to_wd:nn { 16em }
                  { \hfil \use:c { __xdu_ #3 _family : } \zihao { #4 } #5 \hfil }
              }
          }
        \hfil
      }
  }
\bool_new:N \l__xdu_is_ent_bool
\bool_new:N \l__xdu_is_wide_bool
\ctex_at_end_preamble:n
  {
    \tl_if_blank:VF \l__xdu_supv_dept_str
      { \bool_set_true:N \l__xdu_is_wide_bool }
    \tl_if_blank:VF \l__xdu_supv_ent_str
      { \bool_set_true:N \l__xdu_is_wide_bool }
    \tl_if_blank:VF \l__xdu_supv_sch_str
      { \bool_set_true:N \l__xdu_is_wide_bool }
    \cs_new:Npn \__xdu_cover_iii:nnnn #1#2#3#4
      {
        \bool_if:NTF \l__xdu_is_wide_bool
          { \__xdu_cover_iii:nnnnn { 6em } { #1 } { #2 } { #3 } { #4 } }
          { \__xdu_cover_iii:nnnnn { 4em } { #1 } { #2 } { #3 } { #4 } }
      }
  }
\RenewDocumentCommand { \frontmatter } { } { }
\cs_new:Npn \__xdu_frontmatter:
  {
    \loadgeometry { cover }
    \pagestyle    { empty }
    \dim_set:Nn \parindent { 0pt }
    \__xdu_cover_i:nn   { 班级 } { \l__xdu_class_id_str   }
    \__xdu_cover_i:nn   { 学号 } { \l__xdu_student_id_str }
    \skip_vertical:n { 30pt }
    \__xdu_cover_ii:nnn { 65pt } { 35pt } { text }
    \vbox_to_ht:nn { 90pt }
      {
        \mode_leave_vertical:
        \hfil
        \hbox_to_wd:nn { 375pt } { \sffamily \zihao { 0 } 本科毕业设计论文 }
        \hfil
      }
    \__xdu_cover_ii:nnn { 140pt } { 120pt } { icon }
    \clist_new:N \l__xdu_title_clist
    \__xdu_split_title:NV \l__xdu_title_clist \l__xdu_title_tl
    \tl_set:Nx \l__xdu_title_i_tl  { \clist_item:Nn  \l__xdu_title_clist { 1 } }
    \tl_set:Nx \l__xdu_title_ii_tl { \clist_item:Nn  \l__xdu_title_clist { 2 } }
    \__xdu_cover_iii:nnnn { 题目 } { sf } { 3 } { \__xdu_bold_math: \l__xdu_title_i_tl }
    \tl_if_blank:VF \l__xdu_title_ii_tl
      { \__xdu_cover_iii:nnnn { } { sf } { 3 } { \__xdu_bold_math: \l__xdu_title_ii_tl } }
    \__xdu_cover_iii:nnnn { 学院     } { rm } { -3 } { \l__xdu_dept_str   }
    \__xdu_cover_iii:nnnn { 专业     } { rm } { -3 } { \l__xdu_major_str  }
    \__xdu_cover_iii:nnnn { 学生姓名 } { rm } { -3 } { \l__xdu_author_str }
    \tl_if_blank:VF \l__xdu_supv_ent_str
      { \bool_set_true:N \l__xdu_is_ent_bool }
    \tl_if_blank:VF \l__xdu_supv_sch_str
      { \bool_set_true:N \l__xdu_is_ent_bool }
    \bool_if:NTF \l__xdu_is_ent_bool
      {
        \__xdu_cover_iii:nnnn { 校外导师姓名 } { rm } { -3 } { \l__xdu_supv_ent_str }
        \__xdu_cover_iii:nnnn { 校内导师姓名 } { rm } { -3 } { \l__xdu_supv_sch_str }
      }
      {
        \__xdu_cover_iii:nnnn { 导师姓名 } { rm } { -3 } { \l__xdu_supv_str }
        \tl_if_blank:VF \l__xdu_supv_dept_str
          {
            \__xdu_cover_iii:nnnn
              { 院内导师姓名        }
              { rm                  }
              { -3                  }
              { \l__xdu_supv_dept_str }
          }
      }
    \cleardoublepage
    \__xdu_load_main_geometry:
    \pagestyle     { plain }
    \pagenumbering { roman }
    \__xdu_lang_switch:nn
      { \__xdu_n_chapter_head:nn { 摘要 } { 摘 { \quad } 要 } }
      {
        \__xdu_n_chapter_head_ii:nnn
          { 摘要 }
          { 摘 { \quad } 要 }
          { \__xdu_sf_family: \zihao { 3 } \centering }
      }
    \group_begin:
      \dim_set:Nn \parindent { 2 \ccwd }
      \rmfamily \zihao { -4 }
      \file_if_exist_input:n { \l__xdu_abstract_zh_tl }
    \group_end:
    \cs_new:Npn \__xdu_keywords_space: { \hspace { 2em plus 1em minus 1em } }
    \group_begin:
      \sffamily \__xdu_bold_math: \zihao { -4 } \par
      \__xdu_typeout_keywords:nNn
        { 关键词： } { \l__xdu_keywords_zh_clist } { \__xdu_keywords_space: }
    \group_end:
    \cleardoublepage
    \__xdu_n_chapter_head_ii:nn
      { ABSTRACT } { \rmfamily \zihao { 3 } \bfseries \centering }
    \group_begin:
      \dim_set:Nn \parindent { 2 \ccwd }
      \rmfamily \zihao { -4 }
      \file_if_exist_input:n { \l__xdu_abstract_en_tl }
    \group_end:
    \group_begin:
      \rmfamily \zihao { -4 } \bfseries \__xdu_bold_math: \par
      \__xdu_typeout_keywords:nNn
        { Keywords:~ } { \l__xdu_keywords_en_clist } { \__xdu_keywords_space: }
    \group_end:
    \cleardoublepage
    \setcounter { tocdepth } { 5 }
    \__xdu_n_chapter_head:nn
      { \__xdu_lang_switch:nn { 目录            } { Contents } }
      { \__xdu_lang_switch:nn { 目 { \quad } 录 } { Contents } }
    \@starttoc { toc }
    \cleardoublepage
  }
\RenewDocumentCommand { \mainmatter } { } { }
\cs_new:Npn \__xdu_mainmatter:
  {
    \__xdu_load_main_geometry:
    \pagestyle     { plain  }
    \pagenumbering { arabic }
    \dim_set:Nn \parindent { 2 \ccwd }
    \rmfamily \zihao { -4 }
  }
\RenewDocumentCommand { \backmatter } { } { }
\cs_new:Npn \__xdu_backmatter:
  {
    \__xdu_n_chapter_head_toc:nn
      { \__xdu_lang_switch:nn { 致谢            } { Acknowledgements } }
      { \__xdu_lang_switch:nn { 致 { \quad } 谢 } { Acknowledgements } }
    \group_begin:
      \dim_set:Nn \parindent { 2 \ccwd }
      \rmfamily \zihao { -4 }
      \file_if_exist_input:n { \l__xdu_ack_tl }
    \group_end:
    \cs_set:Npn \bibname { \__xdu_lang_switch:nn { 参考文献 } { Bibliography } }
    \__xdu_n_chapter_head_toc:n { \bibname }
    \group_begin:
      \tl_if_eq:NnTF \l__xdu_bib_tool_tl { bibtex }
        {
          \dim_set:Nn \labelsep { 1ex }
          \bibliography { \l__xdu_bib_file_clist }
        }
        { \printbibliography }
    \group_end:
    \__xdu_appendix:
  }
\ctex_after_end_preamble:n { \__xdu_frontmatter: \__xdu_mainmatter: }
\AtEndDocument             { \__xdu_backmatter:                  }
%% 
%%
%% End of file `xduugthesis.cls'.
