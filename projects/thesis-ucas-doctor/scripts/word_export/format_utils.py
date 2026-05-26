from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def parse_braced(text: str, start: int) -> Tuple[str, int]:
    if start >= len(text) or text[start] != "{":
        raise ValueError("parse_braced expects '{' at start")

    depth = 0
    i = start
    out: List[str] = []

    while i < len(text):
        ch = text[i]
        if ch == "\\":
            if i + 1 < len(text):
                out.append(text[i : i + 2])
                i += 2
                continue
            out.append(ch)
            i += 1
            continue

        if ch == "{":
            depth += 1
            if depth > 1:
                out.append(ch)
            i += 1
            continue

        if ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        i += 1

    raise ValueError("unbalanced braces")


CJK_CHAR_RE = r"\u3400-\u9fff\uf900-\ufaff"
CJK_NUMERIC_TOKEN_RE = r"[+-]?\d+(?:\.\d+)?(?:[-–—]\d+(?:\.\d+)?)?"


def _normalize_cjk_number_classifier_spacing(text: str) -> str:
    """Remove spaces around numbers embedded in Chinese classifier phrases."""
    if not text:
        return text
    text = re.sub(
        rf"(?<=[{CJK_CHAR_RE}])\s+({CJK_NUMERIC_TOKEN_RE})\s+(?=[{CJK_CHAR_RE}])",
        r"\1",
        text,
    )
    text = re.sub(
        rf"(?<=[{CJK_CHAR_RE}])\s+({CJK_NUMERIC_TOKEN_RE})(?=[{CJK_CHAR_RE}])",
        r"\1",
        text,
    )
    text = re.sub(
        rf"(?<=[{CJK_CHAR_RE}])({CJK_NUMERIC_TOKEN_RE})\s+(?=[{CJK_CHAR_RE}])",
        r"\1",
        text,
    )
    return text


def parse_macro_args(text: str, macro: str, n_args: int) -> Optional[List[str]]:
    pat = re.compile(r"\\" + re.escape(macro) + r"\s*")
    m = pat.search(text)
    if not m:
        return None

    i = m.end()
    args: List[str] = []
    for _ in range(n_args):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            return None
        value, i = parse_braced(text, i)
        args.append(value)
    return args


def parse_bracketed(text: str, start: int) -> Tuple[str, int]:
    if start >= len(text) or text[start] != "[":
        raise ValueError("parse_bracketed expects '[' at start")

    depth = 0
    i = start
    out: List[str] = []

    while i < len(text):
        ch = text[i]
        if ch == "\\":
            if i + 1 < len(text):
                out.append(text[i : i + 2])
                i += 2
                continue
            out.append(ch)
            i += 1
            continue

        if ch == "[":
            depth += 1
            if depth > 1:
                out.append(ch)
            i += 1
            continue

        if ch == "]":
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        i += 1

    raise ValueError("unbalanced brackets")


def latex_inline_to_text(text: str) -> str:
    subscript_map = str.maketrans(
        {
            "0": "₀",
            "1": "₁",
            "2": "₂",
            "3": "₃",
            "4": "₄",
            "5": "₅",
            "6": "₆",
            "7": "₇",
            "8": "₈",
            "9": "₉",
            "+": "₊",
            "-": "₋",
            "=": "₌",
            "(": "₍",
            ")": "₎",
        }
    )
    superscript_map = str.maketrans(
        {
            "0": "⁰",
            "1": "¹",
            "2": "²",
            "3": "³",
            "4": "⁴",
            "5": "⁵",
            "6": "⁶",
            "7": "⁷",
            "8": "⁸",
            "9": "⁹",
            "+": "⁺",
            "-": "⁻",
            "=": "⁼",
            "(": "⁽",
            ")": "⁾",
        }
    )
    reverse_subscript_map = str.maketrans(
        {
            "₀": "0",
            "₁": "1",
            "₂": "2",
            "₃": "3",
            "₄": "4",
            "₅": "5",
            "₆": "6",
            "₇": "7",
            "₈": "8",
            "₉": "9",
            "₊": "+",
            "₋": "-",
            "₌": "=",
            "₍": "(",
            "₎": ")",
        }
    )
    reverse_superscript_map = str.maketrans(
        {
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
            "⁺": "+",
            "⁻": "-",
            "⁼": "=",
            "⁽": "(",
            "⁾": ")",
        }
    )

    def _to_script(raw: str, table: Dict[int, str]) -> Optional[str]:
        payload = (raw or "").strip()
        if not payload:
            return ""
        converted = payload.translate(table)
        return converted if len(converted) == len(payload) else None

    def _convert_simple_math_script_chunk(chunk: str) -> Optional[str]:
        """Convert inline math chunks like ^{2+}, _{4}^{2-}, ^+ to plain Unicode scripts.

        Return None when chunk is not a pure script sequence.
        """
        s = (chunk or "").strip()
        if not s or s[0] not in {"_", "^"}:
            return None

        out: List[str] = []
        i = 0
        while i < len(s):
            marker = s[i]
            if marker not in {"_", "^"}:
                return None
            i += 1
            while i < len(s) and s[i].isspace():
                i += 1
            if i >= len(s):
                return None

            if s[i] == "{":
                j = s.find("}", i + 1)
                if j == -1:
                    return None
                raw = s[i + 1 : j].strip()
                i = j + 1
            else:
                raw = s[i]
                i += 1

            table = subscript_map if marker == "_" else superscript_map
            converted = _to_script(raw, table)
            if converted is None:
                return None
            out.append(converted)

            while i < len(s) and s[i].isspace():
                i += 1

        return "".join(out)

    def _normalize_soil_notation(text_value: str) -> str:
        """Normalize chemistry/unit strings to common Chinese soil-writing plain notation.

        Goal: avoid OMML and avoid mixed Unicode super/sub-script visual artifacts in Word.
        """
        text_value = text_value.replace("−", "-")
        text_value = text_value.translate(reverse_subscript_map)

        def _superscript_seq_repl(m: re.Match[str]) -> str:
            prefix = m.group(1)
            raw = m.group(2)
            plain = raw.translate(reverse_superscript_map)
            if re.fullmatch(r"\d+[+-]", plain):
                return f"{prefix}^{plain}"
            if plain in {"+", "-"}:
                return f"{prefix}{plain}"
            if re.fullmatch(r"\d+", plain):
                return f"{prefix}{plain}"
            return f"{prefix}^{plain}"

        text_value = re.sub(r"([A-Za-z0-9\)\]])([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾]+)", _superscript_seq_repl, text_value)

        # 常见离子/化学式
        repl = {
            "NO3^-": "NO3-",
            "NH4^+": "NH4+",
            "HCO3^-": "HCO3-",
            "CO3^2-": "CO3^2-",
            "SO4^2-": "SO4^2-",
            "H⁺": "H+",
            "OH⁻": "OH-",
            "H^+": "H+",
            "OH^-": "OH-",
            "Ca^2+": "Ca2+",
            "Mg^2+": "Mg2+",
            "K2CO3": "K2CO3",
            "P2O5": "P2O5",
            "K2O": "K2O",
            "NH4NO3": "NH4NO3",
            "NO2^-": "NO2-",
        }
        for src, dst in repl.items():
            text_value = text_value.replace(src, dst)

        # 常见面积单位写法：DOCX 后处理会把 ^2 转为 Word 字符级上标。
        text_value = text_value.replace("hm²", "hm^2")
        text_value = text_value.replace("km²", "km^2")
        text_value = text_value.replace("m²", "m^2")
        # Keep area-rate units in slash form; users expect kg/hm² rather than kg hm^-2.
        text_value = text_value.replace("kg/hm2", "kg/hm^2")
        text_value = text_value.replace("g/hm2", "g/hm^2")
        text_value = text_value.replace("mg/hm2", "mg/hm^2")

        return text_value

    def _safe_float(raw: str) -> float:
        try:
            return float(raw)
        except Exception:
            return 0.0

    def _blank_len(value: float, unit: str) -> int:
        if unit == "cm":
            return max(4, min(40, int(round(value * 2.6))))
        return max(2, min(20, int(round(value * 1.8))))

    def _indent_len(value: float, unit: str) -> int:
        if unit == "cm":
            return max(1, min(8, int(round(value / 0.9))))
        return max(1, min(8, int(round(value))))

    def _underline_hspace_repl(m: re.Match[str]) -> str:
        value = _safe_float(m.group(1))
        unit = m.group(2).lower()
        return "＿" * _blank_len(value, unit)

    def _hspace_repl(m: re.Match[str]) -> str:
        value = _safe_float(m.group(1))
        unit = m.group(2).lower()
        return "　" * _indent_len(value, unit)

    def _unit_repl(m: re.Match[str]) -> str:
        numerator = m.group(1)
        denominator = m.group(2)
        return f"{numerator}/{denominator}"

    # 表单类文本常用占位宏：将 \underline{\hspace{...}} 转为可填写横线，避免 "3.0cm" 残留进 Word。
    text = re.sub(
        r"\\underline\{\s*\\hspace\*?\{\s*([0-9]+(?:\.[0-9]+)?)\s*(cm|em)\s*\}\s*\}",
        _underline_hspace_repl,
        text,
    )
    # 普通 \hspace/\hspace* 作为缩进占位时，转为全角空格，避免 "2em" 文本化输出。
    text = re.sub(
        r"\\hspace\*?\{\s*([0-9]+(?:\.[0-9]+)?)\s*(cm|em)\s*\}",
        _hspace_repl,
        text,
    )

    text = re.sub(
        r"\b([A-Za-z]+)\s+([A-Za-z]+)\s*\$?\s*\^\s*\{?\s*-\s*1\s*\}?\s*\$?",
        _unit_repl,
        text,
    )
    text = re.sub(r"\$\s*\\(?:rightarrow|to|Rightarrow)(?![A-Za-z])\s*\$", "→", text)
    text = re.sub(r"\\(?:rightarrow|to|Rightarrow)(?![A-Za-z])", "→", text)
    text = re.sub(r"\$\s*\^\s*\\circ\s*\$\s*C", "°C", text)
    text = re.sub(r"\$\s*\\circ\s*\$\s*C", "°C", text)
    text = re.sub(r"\$\s*\^\s*\\circ\s*\$", "°", text)
    text = re.sub(r"\$\s*\\circ\s*\$", "°", text)
    text = re.sub(r"\\textcelsius\s*\{\s*\}", "℃", text)
    text = re.sub(r"\\textmu\s*\{\s*\}", "μ", text)
    text = re.sub(r"\\textmu\b", "μ", text)
    text = text.replace("\\textcelsius", "℃")
    text = text.replace("\\Delta", "Δ")
    text = text.replace("\\eta", "η")
    text = text.replace("\\alpha", "α")
    text = text.replace("\\beta", "β")
    text = text.replace("\\epsilon", "ε")
    text = text.replace("\\gamma", "γ")
    text = text.replace("\\geq", "≥")
    text = text.replace("\\ge", "≥")
    text = text.replace("\\leq", "≤")
    text = text.replace("\\le", "≤")
    text = text.replace("\\log", "log")
    text = text.replace("\\mu", "μ")
    text = text.replace("\\pm", "±")
    text = text.replace("\\rho", "ρ")
    text = text.replace("\\sigma", "σ")
    text = text.replace("\\sim", "∼")
    text = text.replace("\\times", "×")
    text = text.replace("\\cdot", "·")
    text = text.replace("\\%", "%")
    text = text.replace("\\LaTeX", "LaTeX")
    text = text.replace("\\quad", " ")
    text = text.replace("\\qquad", "  ")
    text = re.sub(r"\\[,;:!]\s*", "", text)
    text = text.replace("\\~{}", "__BENSZ_LITERAL_TILDE__")
    text = text.replace("\\\\", " / ")
    text = re.sub(r"\$\s*([<>≤≥=])\s*\$", r"\1", text)
    text = re.sub(
        r"\$([A-Za-z]+)_\{\s*\\(?:text|mathrm)\{([^{}]+)\}\s*\}\$",
        lambda m: f"{m.group(1)}{m.group(2).strip()}",
        text,
    )

    for cmd in ["textit", "emph"]:
        text = re.sub(r"\\" + cmd + r"\{([^{}]*)\}", r"*\1*", text)

    for cmd in ["mathrm", "text"]:
        text = re.sub(r"\\" + cmd + r"\{([^{}]*)\}", r"\1", text)

    for cmd in ["textbf", "underline", "texttt", "mbox", "textrm"]:
        text = re.sub(r"\\" + cmd + r"\{([^{}]*)\}", r"\1", text)

    # 学名缩写兜底：确保 A. selengensis 在 Word 中保持斜体。
    text = re.sub(r"(?<![\w*])A\.\s*selengensis(?![\w])", r"*A. selengensis*", text)

    def _textsubscript_repl(m: re.Match[str]) -> str:
        raw = m.group(1)
        converted = _to_script(raw, subscript_map)
        return converted if converted is not None else f"_{raw}"

    def _textsuperscript_repl(m: re.Match[str]) -> str:
        raw = (m.group(1) or "").strip()
        if raw in {"--", "-"}:
            raw = "-"
        elif raw in {"++", "+"}:
            raw = "+"
        else:
            charge_match = re.fullmatch(r"(\d+)(--|\+\+|-|\+)", raw)
            if charge_match:
                number, sign = charge_match.groups()
                raw = number + ("-" if sign.startswith("-") else "+")

        converted = _to_script(raw, superscript_map)
        return converted if converted is not None else f"^{raw}"

    text = re.sub(r"\\textsubscript\{([^{}]*)\}", _textsubscript_repl, text)
    text = re.sub(r"\\textsuperscript\{([^{}]*)\}", _textsuperscript_repl, text)
    # 兼容诸如 K_2CO_3 / P_2O_5 这类已退化为下划线索引的文本。
    text = re.sub(
        r"(?<=[A-Za-z\)])_([0-9()]+)",
        lambda m: (m.group(1).strip() if m.group(1).strip() else m.group(0)),
        text,
    )
    def _plain_inline_math_repl(m: re.Match[str]) -> str:
        raw = (m.group(1) or "").strip()
        script = _convert_simple_math_script_chunk(raw)
        if script is not None:
            return script

        expr = raw
        expr = expr.replace("\\geq", "≥").replace("\\ge", "≥")
        expr = expr.replace("\\leq", "≤").replace("\\le", "≤")
        expr = re.sub(r"\\(?:mathrm|text)\{([^{}]*)\}", r"\1", expr)
        expr = re.sub(r"\\[,;:!]\s*", "", expr)
        expr = expr.replace("{", "").replace("}", "")
        expr = re.sub(r"\s+", " ", expr).strip()

        ph_bound = re.fullmatch(r"pH\s*(<=|>=|[<>≤≥=])\s*(\d+(?:\.\d+)?)", expr)
        if ph_bound:
            op, value = ph_bound.groups()
            if op in {"≤", "≥", "<=", ">="}:
                return f"pH {op} {value}"
            return f"pH{op}{value}"

        if re.fullmatch(r"[rPn]", expr):
            return f"*{expr}*"
        if re.fullmatch(r"R\s*\^\s*2", expr):
            return "R^2"
        if re.fullmatch(r"η\s*\^\s*2", expr):
            return "η^2"
        if _is_simple_stat_inline_math(raw):
            return _plainify_simple_stat_inline_math(raw)
        if _is_simple_stat_inline_math(expr):
            return _plainify_simple_stat_inline_math(expr)

        return m.group(0)

    # 将形如 Ca$^{2+}$、SO$_4^{2-}$ 的“纯上下标数学块”转为普通文本，
    # 并将简单 pH 阈值、统计符号转成非 OMML 文本。
    text = re.sub(r"\$([^$\n]+)\$", _plain_inline_math_repl, text)
    text = re.sub(r"\\url\{([^{}]*)\}", r"<\1>", text)
    text = re.sub(r"\\path\{([^{}]*)\}", r"`\1`", text)
    text = re.sub(r"\\verb(.)(.*?)\1", r"`\2`", text)

    text = re.sub(r"\\gls\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\autoref\{([^{}]*)\}", r"见 \1", text)

    def _cite_repl(m: re.Match[str]) -> str:
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        if not keys:
            return ""
        return "[" + "; ".join(f"@{k}" for k in keys) + "]"

    # 统一兼容常见 biblatex/natbib 引文命令，供 pandoc --citeproc 解析。
    cite_macros = [
        "cite",
        "parencite",
        "textcite",
        "autocite",
        "footcite",
        "supercite",
        "citep",
        "citet",
        "smartcite",
    ]
    for macro in cite_macros:
        text = re.sub(
            r"\\" + macro + r"\*?(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^{}]+)\}",
            _cite_repl,
            text,
        )
    text = re.sub(r"\\[a-zA-Z@]+\*?", "", text)
    text = re.sub(r"\$([μΔη±])\$", r"\1", text)
    # 避免作者通讯标记（如 "Duan*."/"J*,"）被 Markdown 误判为强调分隔符，
    # 导致后续期刊名斜体闭合错位（例如 "Agriculture*"）。
    text = re.sub(r"([A-Za-z])\*([,.;:])(\s+)([A-Z])", r"\1\\*\2\3\4", text)
    text = text.replace("~", " ")
    text = text.replace("__BENSZ_LITERAL_TILDE__", "~")
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s*\$\$\s*", " → ", text)
    text = _normalize_soil_notation(text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _strip_macro_calls(text: str, macro: str) -> str:
    pattern = re.compile(r"\\" + re.escape(macro) + r"\s*")
    cursor = 0
    chunks: List[str] = []

    while True:
        match = pattern.search(text, cursor)
        if not match:
            chunks.append(text[cursor:])
            break

        chunks.append(text[cursor : match.start()])
        i = match.end()
        while i < len(text) and text[i].isspace():
            i += 1
        if i < len(text) and text[i] == "{":
            try:
                _, i = parse_braced(text, i)
            except Exception:
                chunks.append(text[match.start() : match.end()])
                cursor = match.end()
                continue
        else:
            chunks.append(text[match.start() : match.end()])
        cursor = i

    return "".join(chunks)


def _extract_graphicspaths(text: str) -> List[str]:
    args = parse_macro_args(text, "graphicspath", 1)
    if not args:
        return []

    paths: List[str] = []
    for item in re.findall(r"\{([^{}]+)\}", args[0]):
        normalized = item.strip().replace("\\", "/")
        if normalized:
            paths.append(normalized)
    return paths


def _parse_includegraphics_path(text: str) -> Optional[str]:
    pattern = re.compile(r"\\includegraphics\s*")
    match = pattern.search(text)
    if not match:
        return None

    i = match.end()
    while i < len(text) and text[i].isspace():
        i += 1
    if i < len(text) and text[i] == "[":
        try:
            _, i = parse_bracketed(text, i)
        except Exception:
            return None
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "{":
        return None
    try:
        path, _ = parse_braced(text, i)
    except Exception:
        return None
    return path.strip()


def _candidate_image_names(path_text: str) -> List[Path]:
    base = Path(path_text.strip())
    if not str(base):
        return []
    candidates = [base]
    if base.suffix:
        return candidates
    for suffix in [".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"]:
        candidates.append(Path(f"{path_text}{suffix}"))
    return candidates


def _make_project_relative(path: Path, project_dir: Path) -> str:
    try:
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _resolve_graphics_path(
    image_path: str,
    project_dir: Path,
    tex_path: Path,
    graphicspaths: List[str],
) -> str:
    image_path = image_path.strip()
    if not image_path:
        return image_path

    candidates = _candidate_image_names(image_path)
    search_roots: List[Path] = [project_dir, tex_path.parent]

    for prefix in graphicspaths:
        raw_prefix = prefix.strip()
        if not raw_prefix:
            continue
        search_roots.append(project_dir / raw_prefix)
        search_roots.append(tex_path.parent / raw_prefix)

    seen: Set[str] = set()
    deduped_roots: List[Path] = []
    for root in search_roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped_roots.append(root)

    for candidate in candidates:
        if candidate.is_absolute() and candidate.exists():
            return _make_project_relative(candidate, project_dir)

    for root in deduped_roots:
        for candidate in candidates:
            full_path = (root / candidate).resolve()
            if full_path.exists():
                return _make_project_relative(full_path, project_dir)

    return image_path.replace("\\", "/")


INLINE_FIGURE_MACRO_NAME_RE = re.compile(r"\\[A-Za-z@]+InlineFigure$")
INLINE_FIGURE_MACRO_USE_RE = re.compile(r"\\([A-Za-z@]+InlineFigure)\b")
INLINE_TABLE_MACRO_USE_RE = re.compile(r"\\([A-Za-z@]+InlineTable)\b")
NOTE_MACRO_USE_RE = re.compile(r"\\Bensz(?:Figure|Table|Caption)Note\b")
MINIPAGE_ENV_RE = re.compile(r"\\begin\{minipage\}\{[^{}]*\}(.*?)\\end\{minipage\}", re.S)
INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+?)(?<!\\)\$(?!\$)")


def _parse_optional_and_braced_args(
    text: str,
    start: int,
    required_args: int,
) -> Optional[Tuple[int, Optional[str], List[str]]]:
    i = start
    while i < len(text) and text[i].isspace():
        i += 1

    optional_arg: Optional[str] = None
    if i < len(text) and text[i] == "[":
        try:
            optional_arg, i = parse_bracketed(text, i)
        except Exception:
            return None

    args: List[str] = []
    for _ in range(required_args):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            return None
        try:
            value, i = parse_braced(text, i)
        except Exception:
            return None
        args.append(value)

    return i, optional_arg, args


def _strip_inline_figure_macro_definitions(text: str) -> str:
    pattern = re.compile(r"\\(?:re)?newcommand\s*")
    cursor = 0
    chunks: List[str] = []

    while True:
        match = pattern.search(text, cursor)
        if not match:
            chunks.append(text[cursor:])
            break

        chunks.append(text[cursor : match.start()])
        i = match.end()
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            chunks.append(text[match.start() : match.end()])
            cursor = match.end()
            continue

        try:
            macro_spec, i = parse_braced(text, i)
        except Exception:
            chunks.append(text[match.start() : match.end()])
            cursor = match.end()
            continue

        macro_name = macro_spec.strip()
        if not INLINE_FIGURE_MACRO_NAME_RE.fullmatch(macro_name):
            chunks.append(text[match.start():i])
            cursor = i
            continue

        while i < len(text) and text[i].isspace():
            i += 1
        if i < len(text) and text[i] == "[":
            try:
                _, i = parse_bracketed(text, i)
            except Exception:
                chunks.append(text[match.start() : match.end()])
                cursor = match.end()
                continue

        while i < len(text) and text[i].isspace():
            i += 1
        if i < len(text) and text[i] == "[":
            try:
                _, i = parse_bracketed(text, i)
            except Exception:
                chunks.append(text[match.start() : match.end()])
                cursor = match.end()
                continue

        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            chunks.append(text[match.start() : match.end()])
            cursor = match.end()
            continue

        try:
            _, i = parse_braced(text, i)
        except Exception:
            chunks.append(text[match.start() : match.end()])
            cursor = match.end()
            continue

        cursor = i

    return "".join(chunks)


def _is_simple_stat_inline_math(expr: str) -> bool:
    candidate = expr.strip()
    if not candidate:
        return False

    # 仅允许统计表达常见转义；其余带命令的数学对象保持原样。
    tmp = (
        candidate.replace(r"\%", "")
        .replace(r"\leq", "≤")
        .replace(r"\geq", "≥")
        .replace(r"\le", "≤")
        .replace(r"\ge", "≥")
        .replace(r"\eta", "η")
        .replace(r"\rho", "ρ")
        .replace(r"\varrho", "ρ")
        .replace(r"\alpha", "α")
        .replace(r"\beta", "β")
        .replace(r"\gamma", "γ")
        .replace(r"\sim", "∼")
        .replace(r"\times", "×")
    )
    tmp = tmp.replace("{", "").replace("}", "")
    if "\\" in tmp:
        return False

    token_candidate = (
        candidate.replace(r"\leq", "≤")
        .replace(r"\geq", "≥")
        .replace(r"\le", "≤")
        .replace(r"\ge", "≥")
        .replace(r"\eta", "η")
        .replace(r"\rho", "ρ")
        .replace(r"\varrho", "ρ")
        .replace(r"\alpha", "α")
        .replace(r"\beta", "β")
        .replace(r"\gamma", "γ")
    )
    has_stat_token = re.search(r"\b(?:P|p|r|R|n|N|F|t|T|D|d)\b|η|ρ|α|β|γ", token_candidate) is not None
    has_comparator = re.search(r"[=<>≤≥]", token_candidate) is not None
    if has_stat_token and has_comparator:
        return True

    # 百分比改变量，如 -7.6\%
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?\\%", candidate):
        return True

    # 置信区间的简单数值区间，如 [-0.97, -0.66]
    if re.fullmatch(r"\[\s*[+-]?\d+(?:\.\d+)?\s*,\s*[+-]?\d+(?:\.\d+)?\s*\]", candidate):
        return True

    return False


def _plainify_simple_stat_inline_math(expr: str) -> str:
    plain = (
        expr.replace(r"\%", "%")
        .replace(r"\leq", "≤")
        .replace(r"\geq", "≥")
        .replace(r"\le", "≤")
        .replace(r"\ge", "≥")
        .replace(r"\eta", "η")
        .replace(r"\rho", "ρ")
        .replace(r"\varrho", "ρ")
        .replace(r"\alpha", "α")
        .replace(r"\beta", "β")
        .replace(r"\gamma", "γ")
        .replace(r"\sim", "∼")
        .replace(r"\times", "×")
    )
    plain = plain.replace("{", "").replace("}", "")
    plain = re.sub(r"η\s*\^\s*2", "η²", plain)
    plain = re.sub(r"η\s*\^\s*3", "η³", plain)
    plain = re.sub(r"ρ\s*\^\s*2", "ρ²", plain)
    plain = re.sub(r"ρ\s*\^\s*3", "ρ³", plain)
    plain = re.sub(r"\s*(<=|>=|[=<>≤≥])\s*", r" \1 ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return _italicize_plain_stat_tokens(plain)


def _normalize_simple_stat_inline_math(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        if not _is_simple_stat_inline_math(expr):
            return match.group(0)

        return _plainify_simple_stat_inline_math(expr)

    return INLINE_MATH_RE.sub(_repl, text)


def _italicize_plain_stat_tokens(text: str) -> str:
    if not text:
        return text
    return re.sub(
        r"(?<![A-Za-z*])([PpRrNnFfTtWwDd])(?=\s*(?:<=|>=|[=<>≤≥]))(?!\*)",
        lambda m: f"*{m.group(1)}*",
        text,
    )


def _format_chapter_sequence(chapter_no: int, item_no: int) -> str:
    if chapter_no > 0:
        return f"{chapter_no}-{item_no}"
    return str(item_no)


def _format_export_sequence(chapter_no: int, item_no: int, *, appendix_mode: bool = False) -> str:
    if appendix_mode:
        appendix_chapter = chapter_no if chapter_no > 0 else 1
        return f"{appendix_chapter}-{item_no}"
    return _format_chapter_sequence(chapter_no, item_no)


def _format_caption_marker_sequence(chapter_no: int, item_no: int, *, appendix_mode: bool = False) -> str:
    if appendix_mode:
        appendix_chapter = chapter_no if chapter_no > 0 else 1
        return f"A{appendix_chapter}-{item_no}"
    return _format_chapter_sequence(chapter_no, item_no)


def _build_caption_marker(kind: str, lang: str, sequence: str, caption: str) -> str:
    return f"[[BENSZ{kind}CAP:{lang}:{sequence}]] {caption.strip()}".rstrip()


def _strip_caption_terminal_punctuation(text: str) -> str:
    stripped = (text or "").strip()
    return re.sub(r"[。．\.]+\s*$", "", stripped)


def _format_caption_text(kind: str, lang: str, sequence: str, caption: str) -> str:
    title = _strip_caption_terminal_punctuation(caption)
    appendix_mode = sequence.startswith("A")
    appendix_index = sequence[1:] if appendix_mode else sequence
    if kind == "FIG" and lang == "zh":
        prefix = f"附图{appendix_index}" if appendix_mode else f"图{sequence}"
    elif kind == "FIG":
        prefix = f"Appendix Figure {appendix_index}" if appendix_mode else f"Figure {sequence}"
    elif lang == "zh":
        prefix = f"附表{appendix_index}" if appendix_mode else f"表{sequence}"
    else:
        prefix = f"Appendix Table {appendix_index}" if appendix_mode else f"Table {sequence}"
    return f"{prefix} {title}" if title else prefix


def _caption_latex_to_text(text: str) -> str:
    text = re.sub(r"\$([^$]+)\$", lambda m: latex_inline_to_text(m.group(1)), text)
    text = latex_inline_to_text(text)
    text = text.replace("$", "")
    text = re.sub(r"\s+", " ", text)
    text = _normalize_cjk_number_classifier_spacing(text)
    return text.strip()




format_caption_text = _format_caption_text
format_export_sequence = _format_export_sequence
