from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import json

from extract_from_tex import extract_research_content_section
from utils import dump_yaml, read_text, write_text


AI_TEX_REQUEST_MD = "ai_tex_request.md"
AI_TEX_RESPONSE_JSON = "ai_tex_response.json"
DEFAULT_MAX_TEX_CHARS = 20000


def _json_load(path: Path) -> Optional[Dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def prepare_tex_extraction_request(
    tex_path: Path,
    config: Dict[str, Any],
    output_dir: Path,
) -> Tuple[Path, Path]:
    """
    Emit an offline TEX extraction protocol (NO external model calls).

    Files:
    - ai_tex_request.md: contains TEX content (prefer key section) + instructions + schema
    - ai_tex_response.json: response template for host AI to fill (contains spec_draft)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    req = output_dir / AI_TEX_REQUEST_MD
    resp = output_dir / AI_TEX_RESPONSE_JSON

    # Always overwrite request to match current tex/config; keep response if already filled.
    section = ""
    try:
        section = extract_research_content_section(tex_path) or ""
    except Exception:
        section = ""
    if not section.strip():
        # Fallback to full text (may be large; host AI can still decide to skim).
        try:
            section = read_text(tex_path)
        except Exception:
            section = ""

    planning = config.get("planning", {}) if isinstance(config.get("planning"), dict) else {}
    extraction = planning.get("extraction", {}) if isinstance(planning.get("extraction"), dict) else {}
    try:
        max_chars = int(extraction.get("ai_tex_max_chars", DEFAULT_MAX_TEX_CHARS) or DEFAULT_MAX_TEX_CHARS)
    except Exception:
        max_chars = DEFAULT_MAX_TEX_CHARS
    max_chars = max(2000, min(200000, max_chars))

    truncated_note = ""
    if len(section) > max_chars:
        truncated_note = f"% [TRUNCATED] TEX content truncated to first {max_chars} chars to avoid context overflow.\n"
        section = section[:max_chars]

    defaults = planning.get("defaults", {}) if isinstance(planning.get("defaults"), dict) else {}
    defaults_hint = {
        "direction": defaults.get("direction", "top-to-bottom"),
        "color_scheme": defaults.get("color_scheme", ""),
        "groups": defaults.get("groups", []),
    }

    req_text = "\n".join(
        [
            "# TEX 结构化提取请求（nsfc-schematic）",
            "",
            "你将读取用户标书 TEX 内容（优先：研究内容章节），理解研究机制后输出结构化原理图草案。",
            "请将结果写入 `ai_tex_response.json`（JSON），其中 `spec_draft` 必须满足 nsfc-schematic 的 spec 结构。",
            "",
            "## 输入",
            "",
            f"- tex_path: `{tex_path}`",
            "",
            "### TEX 内容（请通读理解语义）",
            "",
            "```tex",
            (truncated_note + section).rstrip(),
            "```",
            "",
            "### config 规划默认值提示（YAML）",
            "",
            "```yaml",
            dump_yaml(defaults_hint).rstrip(),
            "```",
            "",
            "## 提取任务",
            "",
            "1. 研究模块划分：2-5 个分组（如输入/处理/输出，或按方法学阶段划分）。",
            "2. 核心节点：每组 1-6 个节点，节点命名需与正文术语一致。",
            "3. 连接关系：反映数据流/流程/因果（避免无意义链式）。",
            "4. 输出要便于画图：节点文案尽量短（建议 <= 12 字），必要时用括号补充。",
            "",
            "## 输出 schema（写入 ai_tex_response.json）",
            "",
            "```json",
            "{",
            "  \"title\": \"原理图标题\",",
            "  \"terms\": [\"术语1\", \"术语2\"],",
            "  \"spec_draft\": {",
            "    \"schematic\": {",
            "      \"title\": \"...\",",
            "      \"direction\": \"top-to-bottom\",",
            "      \"groups\": [",
            "        {\"id\": \"input\", \"label\": \"输入层\", \"style\": \"dashed-border\", \"children\": [{\"id\": \"n1\", \"label\": \"...\"}] }",
            "      ],",
            "      \"edges\": [{\"from\": \"n1\", \"to\": \"n2\", \"label\": \"\"}]",
            "    }",
            "  }",
            "}",
            "```",
            "",
            "约束：",
            "- id 建议使用英文/数字/下划线（避免空格与特殊字符）。",
            "- edges 只引用存在的 node id。",
            "",
        ]
    )
    write_text(req, req_text + "\n")

    if not resp.exists():
        write_text(resp, json.dumps({"title": "", "terms": [], "spec_draft": {}}, ensure_ascii=False, indent=2) + "\n")

    return req, resp


def consume_tex_extraction(resp_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load ai_tex_response.json and return it if it contains a non-empty spec_draft.
    """
    if not resp_path.exists() or not resp_path.is_file():
        return None
    payload = _json_load(resp_path)
    if payload is None:
        return None
    spec_draft = payload.get("spec_draft")
    if not isinstance(spec_draft, dict):
        return None
    if not spec_draft:
        return None
    return payload
