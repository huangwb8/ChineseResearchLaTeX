from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from extract_from_tex import extract_research_content_section, extract_research_terms, find_candidate_tex
from utils import dump_yaml, fatal, info, load_yaml, read_text, skill_root, warn, write_text


@dataclass(frozen=True)
class CheckResult:
    level: str  # OK|WARN|P1|P0
    message: str


def _load_yaml_text(text: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        fatal(
            "缺少依赖 PyYAML，无法解析 spec 草案。\n"
            "请先安装：python3 -m pip install pyyaml\n"
            f"原始错误：{exc}"
        )

    try:
        data = yaml.safe_load(text)
    except Exception as exc:
        fatal(f"解析 YAML 失败（来自 PLAN.md 的 spec 草案）：\n{exc}")
    if not isinstance(data, dict):
        fatal("spec 草案 YAML 根节点必须为 mapping（dict）")
    return data


def _extract_spec_yaml_from_plan_md(plan_md: str) -> Optional[str]:
    # Prefer fenced blocks marked as yaml/yml.
    blocks = re.findall(r"```(?:yaml|yml)\s*(.*?)\s*```", plan_md, flags=re.S | re.I)
    for b in blocks:
        if "schematic:" in b:
            return b.strip() + "\n"

    # Fallback: any fenced block that looks like a schematic spec.
    blocks2 = re.findall(r"```\s*(.*?)\s*```", plan_md, flags=re.S)
    for b in blocks2:
        if "schematic:" in b and "groups" in b and "edges" in b:
            return b.strip() + "\n"
    return None


def _slugify_id(s: str) -> str:
    # Ensure ASCII + stable ids; keep it conservative to match spec_parser.py constraints.
    out = re.sub(r"[^A-Za-z0-9_-]+", "_", s.strip())
    out = out.strip("_")
    if not out:
        return "node"
    if not re.match(r"^[A-Za-z_]", out):
        out = "_" + out
    return out[:64]


def _split_terms_to_groups(terms: List[str]) -> Tuple[List[str], List[str], List[str]]:
    input_terms: List[str] = []
    output_terms: List[str] = []
    process_terms: List[str] = []

    for t in terms:
        s = t.strip()
        if not s:
            continue
        # Heuristics: keep broad to avoid overfitting to a single proposal.
        if re.search(r"(输入|原始|数据|样本|采集|测序|表型|队列|标注|特征)", s):
            input_terms.append(s)
        elif re.search(r"(输出|结果|预测|推断|分类|回归|评分|风险|指标|报告|应用)", s):
            output_terms.append(s)
        else:
            process_terms.append(s)

    return input_terms, process_terms, output_terms


def _build_spec_draft(config: Dict[str, Any], terms: List[str]) -> Dict[str, Any]:
    planning = config.get("planning", {}) if isinstance(config.get("planning"), dict) else {}
    defaults = planning.get("defaults", {}) if isinstance(planning.get("defaults"), dict) else {}

    title = str(defaults.get("title", "NSFC 原理图（规划草案）"))
    direction = str(defaults.get("direction", config.get("layout", {}).get("direction", "top-to-bottom")))

    group_defs = defaults.get("groups")
    if not isinstance(group_defs, list) or not group_defs:
        group_defs = [
            {"id": "input", "label": "输入层", "style": "dashed-border"},
            {"id": "process", "label": "处理层", "style": "solid-border"},
            {"id": "output", "label": "输出层", "style": "background-fill"},
        ]

    max_terms = (
        int((planning.get("extraction", {}) or {}).get("max_terms", 12))
        if isinstance(planning.get("extraction"), dict)
        else 12
    )
    terms = [t.strip() for t in terms if isinstance(t, str) and t.strip()][:max_terms]

    in_terms, proc_terms, out_terms = _split_terms_to_groups(terms)

    # Guarantee minimal input/process/output anchors (planning checks depend on it).
    if not in_terms:
        in_terms = ["输入数据"]
    if not proc_terms:
        proc_terms = ["核心方法"]
    if not out_terms:
        out_terms = ["关键输出"]

    def make_children(group_id: str, role: str, labels: List[str]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for idx, label in enumerate(labels, start=1):
            base = _slugify_id(label.lower())
            nid_base = f"{group_id}_{base}" if not base.startswith(f"{group_id}_") else base
            # Chinese labels often collapse to the same slug ("node"); keep ids stable and unique.
            nid = nid_base
            if base == "node" or nid in seen:
                nid = f"{nid_base}_{idx:02d}"
            # Final de-dup guard (e.g., repeated labels).
            j = 2
            while nid in seen:
                nid = f"{nid_base}_{idx:02d}_{j:02d}"
                j += 1
            nid = nid[:64]
            # Ensure uniqueness even after truncation.
            while nid in seen:
                nid = f"{nid_base}_{idx:02d}_{j:02d}"[:64]
                j += 1
            seen.add(nid)
            kind = "primary"
            if role == "process":
                kind = "critical" if idx == 1 else "secondary"
            if role == "output":
                kind = "critical" if idx == 1 else "primary"
            if role == "input" and re.search(r"(表型|标签|标注)", label):
                kind = "decision"
            out.append({"id": nid, "label": label, "kind": kind})
        return out

    # Normalize group defs and keep ids unique.
    norm_groups: List[Dict[str, Any]] = []
    seen_gids: set[str] = set()
    for idx, gd in enumerate(group_defs, start=1):
        if not isinstance(gd, dict):
            continue
        raw_id = str(gd.get("id", "")).strip() or "group"
        gid_base = _slugify_id(raw_id)
        gid = gid_base
        if gid in seen_gids:
            gid = f"{gid_base}_{idx:02d}"[:64]
        k = 2
        while gid in seen_gids:
            gid = f"{gid_base}_{idx:02d}_{k:02d}"[:64]
            k += 1
        seen_gids.add(gid)

        glabel = str(gd.get("label", raw_id)).strip() or raw_id
        gstyle = str(gd.get("style", "solid-border")).strip() or "solid-border"
        role = "process"
        if gid == "input" or "输入" in glabel:
            role = "input"
        if gid == "output" or "输出" in glabel:
            role = "output"
        norm_groups.append({"id": gid, "label": glabel, "style": gstyle, "role": role})

    # Ensure at least one input/output group. Insert defaults when missing.
    def _find_default_def(role: str) -> Dict[str, Any]:
        for gd in group_defs:
            if not isinstance(gd, dict):
                continue
            rid = str(gd.get("id", "")).strip()
            lab = str(gd.get("label", "")).strip()
            if role == "input" and (rid == "input" or "输入" in lab):
                return gd
            if role == "output" and (rid == "output" or "输出" in lab):
                return gd
            if role == "process" and (rid == "process" or "处理" in lab):
                return gd
        # fallback
        if role == "input":
            return {"id": "input", "label": "输入层", "style": "dashed-border"}
        if role == "output":
            return {"id": "output", "label": "输出层", "style": "background-fill"}
        return {"id": "process", "label": "处理层", "style": "solid-border"}

    def _insert_group(role: str, where: str) -> None:
        d = _find_default_def(role)
        rid = _slugify_id(str(d.get("id", role)).strip() or role)
        base = rid
        k = 2
        while rid in seen_gids:
            rid = f"{base}_{k:02d}"[:64]
            k += 1
        seen_gids.add(rid)
        obj = {
            "id": rid,
            "label": str(d.get("label", rid)).strip() or rid,
            "style": str(d.get("style", "solid-border")).strip() or "solid-border",
            "role": role,
        }
        if where == "front":
            norm_groups.insert(0, obj)
        else:
            norm_groups.append(obj)

    if not any(g.get("role") == "input" for g in norm_groups):
        _insert_group("input", "front")
    if not any(g.get("role") == "output" for g in norm_groups):
        _insert_group("output", "back")
    if not any(g.get("role") == "process" for g in norm_groups):
        # Planning expects at least one "how it works" layer; keep it in the middle.
        d = _find_default_def("process")
        rid = "process"
        k = 2
        while rid in seen_gids:
            rid = f"process_{k:02d}"[:64]
            k += 1
        seen_gids.add(rid)
        obj = {
            "id": rid,
            "label": str(d.get("label", rid)).strip() or rid,
            "style": str(d.get("style", "solid-border")).strip() or "solid-border",
            "role": "process",
        }
        # Insert after the first input group if possible.
        insert_at = 1
        for i, g in enumerate(norm_groups):
            if g.get("role") == "input":
                insert_at = i + 1
                break
        norm_groups.insert(insert_at, obj)

    # Split process terms across process groups (2-5 total groups supported).
    proc_group_ids = [g["id"] for g in norm_groups if g.get("role") == "process" and isinstance(g.get("id"), str)]
    # Keep each group small to stay within readability constraints by default.
    in_terms = in_terms[:4]
    out_terms = out_terms[:4]
    proc_terms = proc_terms[: max(6, 6 * max(1, len(proc_group_ids)))]
    proc_slices: Dict[str, List[str]] = {gid: [] for gid in proc_group_ids}
    if proc_group_ids:
        for i, t in enumerate(proc_terms[: 6 * len(proc_group_ids)]):
            proc_slices[proc_group_ids[i % len(proc_group_ids)]].append(t)

    groups: List[Dict[str, Any]] = []
    for g in norm_groups:
        gid = str(g.get("id", "")).strip() or "group"
        glabel = str(g.get("label", gid)).strip() or gid
        gstyle = str(g.get("style", "solid-border")).strip() or "solid-border"
        role = str(g.get("role", "process"))
        labels: List[str] = []
        if role == "input":
            labels = in_terms
        elif role == "output":
            labels = out_terms
        else:
            labels = proc_slices.get(gid, []) or ["核心方法"]
            labels = labels[:6]
        children = make_children(gid, role, labels)
        groups.append({"id": gid, "label": glabel, "style": gstyle, "children": children})

    # Main flow: first input -> chain process -> first output
    def all_node_ids(gid: str) -> List[str]:
        out_ids: List[str] = []
        for g in groups:
            if g.get("id") != gid:
                continue
            ch = g.get("children")
            if isinstance(ch, list):
                for c in ch:
                    if isinstance(c, dict) and isinstance(c.get("id"), str):
                        out_ids.append(str(c["id"]))
        return out_ids

    def first_node_id(gid: str) -> Optional[str]:
        ids = all_node_ids(gid)
        return ids[0] if ids else None

    def last_node_id(gid: str) -> Optional[str]:
        ids = all_node_ids(gid)
        return ids[-1] if ids else None

    edges: List[Dict[str, Any]] = []
    # Ordered groups: input -> (all process groups in order) -> output
    input_gid = next((str(g["id"]) for g in norm_groups if g.get("role") == "input" and isinstance(g.get("id"), str)), "input")
    output_gid = next((str(g["id"]) for g in norm_groups if g.get("role") == "output" and isinstance(g.get("id"), str)), "output")

    ordered_gids: List[str] = []
    ordered_gids.append(input_gid)
    for ng in norm_groups:
        if ng.get("role") == "process" and isinstance(ng.get("id"), str):
            ordered_gids.append(str(ng["id"]))
    ordered_gids.append(output_gid)

    # Within-group chains.
    for gid in ordered_gids:
        ids = all_node_ids(gid)
        for a, b in zip(ids, ids[1:]):
            edges.append({"from": a, "to": b, "style": "solid"})

    # Between-group links.
    for prev_gid, next_gid in zip(ordered_gids, ordered_gids[1:]):
        prev_last = last_node_id(prev_gid)
        next_first = first_node_id(next_gid)
        if not prev_last or not next_first:
            continue
        style = "thick" if next_gid == output_gid else "solid"
        edges.append({"from": prev_last, "to": next_first, "style": style})

    # Optional auxiliary: other input nodes -> first node of the first process group.
    first_process_gid = next((gid for gid in ordered_gids if gid not in (input_gid, output_gid)), None)
    if first_process_gid:
        target = first_node_id(first_process_gid)
        if target:
            for nid in all_node_ids(input_gid)[1:]:
                edges.append({"from": nid, "to": target, "style": "dashed", "label": "辅助输入"})

    # Optional: last process -> other outputs.
    last_process_gid = None
    for gid in reversed(ordered_gids):
        if gid not in (input_gid, output_gid):
            last_process_gid = gid
            break
    if last_process_gid:
        src = last_node_id(last_process_gid)
        if src:
            for nid in all_node_ids(output_gid)[1:]:
                edges.append({"from": src, "to": nid, "style": "solid"})

    # De-duplicate edges while preserving order to avoid noisy/over-dense specs.
    deduped: List[Dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    for e in edges:
        if not isinstance(e, dict):
            continue
        fr = e.get("from")
        to = e.get("to")
        if not isinstance(fr, str) or not isinstance(to, str):
            continue
        style = str(e.get("style", "solid"))
        label = str(e.get("label", "")) if e.get("label") is not None else ""
        key = (fr, to, style, label)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        deduped.append(e)
    edges = deduped

    return {
        "schematic": {
            "title": title,
            "direction": direction,
            "groups": groups,
            "edges": edges,
        }
    }


def _run_checks(config: Dict[str, Any], spec: Dict[str, Any]) -> List[CheckResult]:
    planning = config.get("planning", {}) if isinstance(config.get("planning"), dict) else {}
    checks = planning.get("checks", {}) if isinstance(planning.get("checks"), dict) else {}

    gmin = int(checks.get("groups_min", 2))
    gmax = int(checks.get("groups_max", 5))
    nmin = int(checks.get("nodes_per_group_min", 1))
    nmax = int(checks.get("nodes_per_group_max", 6))
    total_max = int(checks.get("total_nodes_max", 20))
    dens_ratio = float(checks.get("edge_density_max_ratio", 1.5))
    require_io = bool(checks.get("require_input_output", True))

    root = spec.get("schematic", spec)
    groups = root.get("groups") if isinstance(root, dict) else None
    edges = root.get("edges") if isinstance(root, dict) else None
    if not isinstance(groups, list) or not groups:
        return [CheckResult(level="P0", message="spec.schematic.groups 缺失或为空（无法生成图）")]

    results: List[CheckResult] = []

    # Structural validity checks (fail fast).
    gids: List[str] = []
    for g in groups:
        if isinstance(g, dict) and isinstance(g.get("id"), str):
            gids.append(str(g["id"]))
    if len(gids) != len(set(gids)):
        results.append(CheckResult(level="P0", message="存在重复 group id（会导致解析/渲染不确定）"))

    node_ids: List[str] = []
    for g in groups:
        if not isinstance(g, dict):
            continue
        children = g.get("children")
        if not isinstance(children, list):
            continue
        for c in children:
            if isinstance(c, dict) and isinstance(c.get("id"), str):
                node_ids.append(str(c["id"]))
    if len(node_ids) != len(set(node_ids)):
        results.append(CheckResult(level="P0", message="存在重复 node id（spec_parser 会直接报错）"))

    if isinstance(edges, list) and node_ids:
        id_set = set(node_ids)
        bad = 0
        for e in edges:
            if not isinstance(e, dict):
                continue
            fr = e.get("from")
            to = e.get("to")
            if not isinstance(fr, str) or not isinstance(to, str):
                bad += 1
                continue
            if fr not in id_set or to not in id_set:
                bad += 1
        if bad > 0:
            results.append(CheckResult(level="P0", message=f"存在 {bad} 条 edge 指向不存在的节点（from/to 不在 node 集合内）"))

    if len(groups) < gmin or len(groups) > gmax:
        results.append(CheckResult(level="WARN", message=f"分组数量={len(groups)}（建议范围 {gmin}-{gmax}）"))
    else:
        results.append(CheckResult(level="OK", message=f"分组数量={len(groups)}（OK）"))

    total_nodes = 0
    input_nodes = 0
    output_nodes = 0
    for g in groups:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("id", "")).strip()
        glabel = str(g.get("label", "")).strip()
        children = g.get("children")
        count = len(children) if isinstance(children, list) else 0
        total_nodes += count

        is_input = gid == "input" or "输入" in glabel
        is_output = gid == "output" or "输出" in glabel
        if is_input:
            input_nodes += count
        if is_output:
            output_nodes += count

        if count < nmin or count > nmax:
            results.append(CheckResult(level="WARN", message=f"分组 {gid or glabel}: 节点数={count}（建议范围 {nmin}-{nmax}）"))
        else:
            results.append(CheckResult(level="OK", message=f"分组 {gid or glabel}: 节点数={count}（OK）"))

    if total_nodes > total_max:
        results.append(CheckResult(level="P1", message=f"总节点数={total_nodes} > {total_max}（建议拆分多图）"))
    else:
        results.append(CheckResult(level="OK", message=f"总节点数={total_nodes}（OK）"))

    edge_count = len(edges) if isinstance(edges, list) else 0
    max_edges = int(dens_ratio * max(1, total_nodes))
    if edge_count > max_edges:
        results.append(CheckResult(level="WARN", message=f"连接密度偏高：edges={edge_count} > {dens_ratio:.2f}×nodes≈{max_edges}"))
    else:
        results.append(CheckResult(level="OK", message=f"连接密度：edges={edge_count}（OK）"))

    if require_io:
        if input_nodes <= 0 or output_nodes <= 0:
            results.append(CheckResult(level="P0", message=f"输入/输出节点缺失：input_nodes={input_nodes}, output_nodes={output_nodes}"))
        else:
            results.append(CheckResult(level="OK", message=f"输入/输出节点：input={input_nodes}, output={output_nodes}（OK）"))

    return results


def _format_plan_md(
    config: Dict[str, Any],
    source_label: str,
    extracted_terms: List[str],
    spec: Dict[str, Any],
    checks: List[CheckResult],
) -> str:
    planning = config.get("planning", {}) if isinstance(config.get("planning"), dict) else {}
    defaults = planning.get("defaults", {}) if isinstance(planning.get("defaults"), dict) else {}
    scheme = str(defaults.get("color_scheme", config.get("color_scheme", {}).get("name", "academic-blue")))

    root = spec.get("schematic", spec)
    groups = root.get("groups") if isinstance(root, dict) else []
    edges = root.get("edges") if isinstance(root, dict) else []

    def group_table_rows() -> List[str]:
        rows: List[str] = ["| 模块 ID | 模块名称 | 职责说明 | 节点数 |", "|---|---|---|---|"]
        for g in groups if isinstance(groups, list) else []:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("id", "")).strip()
            glabel = str(g.get("label", "")).strip()
            cnt = len(g.get("children")) if isinstance(g.get("children"), list) else 0
            duty = "（待补充）"
            if gid == "input" or gid.startswith("input") or "输入" in glabel:
                duty = "数据采集与预处理"
            elif gid == "process" or gid.startswith("process") or "处理" in glabel:
                duty = "核心算法/方法"
            elif gid == "output" or gid.startswith("output") or "输出" in glabel:
                duty = "结果输出与应用"
            rows.append(f"| {gid} | {glabel} | {duty} | {cnt} |")
        return rows

    def nodes_tables() -> List[str]:
        out: List[str] = []
        for g in groups if isinstance(groups, list) else []:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("id", "")).strip() or "group"
            glabel = str(g.get("label", "")).strip() or gid
            out.extend([f"### {gid}（{glabel}）", "", "| 节点 ID | 节点名称 | 类型 | 说明 |", "|---|---|---|---|"])
            children = g.get("children") if isinstance(g.get("children"), list) else []
            for c in children:
                if not isinstance(c, dict):
                    continue
                nid = str(c.get("id", "")).strip()
                label = str(c.get("label", "")).strip()
                kind = str(c.get("kind", "primary")).strip()
                out.append(f"| {nid} | {label} | {kind} | （待补充） |")
            out.append("")
        return out

    def edges_section() -> List[str]:
        # Provide a simple main/aux split based on style.
        main: List[str] = []
        aux: List[str] = []
        for e in edges if isinstance(edges, list) else []:
            if not isinstance(e, dict):
                continue
            fr = e.get("from")
            to = e.get("to")
            if not isinstance(fr, str) or not isinstance(to, str):
                continue
            style = str(e.get("style", "solid"))
            if style in {"dashed"}:
                aux.append(f"- {fr} → {to}")
            else:
                main.append(f"- {fr} → {to}")

        out = ["### 主流向（实线/粗线）", ""]
        out.extend(main or ["- （待补充）"])
        out.extend(["", "### 辅助连接（虚线）", ""])
        out.extend(aux or ["- （无）"])
        out.append("")
        return out

    def checks_lines() -> List[str]:
        out: List[str] = []
        worst = "OK"
        order = {"OK": 0, "WARN": 1, "P1": 2, "P0": 3}
        for c in checks:
            worst = c.level if order.get(c.level, 0) > order.get(worst, 0) else worst
        out.append(f"- 总体结论：{worst}")
        out.append("")
        for c in checks:
            out.append(f"- [{c.level}] {c.message}")
        return out

    lines: List[str] = [
        "# 原理图规划草案",
        "",
        f"- input: {source_label}",
        "",
        "## 核心目标",
        "",
        "（一句话描述：这张图要传达什么核心机制/结构/因果链条？）",
        "",
        "## 模块划分",
        "",
        *group_table_rows(),
        "",
        "## 节点清单",
        "",
        *nodes_tables(),
        "## 连接关系",
        "",
        *edges_section(),
        "## 布局建议",
        "",
        f"- 方向：{root.get('direction', 'top-to-bottom') if isinstance(root, dict) else 'top-to-bottom'}",
        "- 层次：输入 → 处理 → 输出",
        f"- 配色：{scheme}",
        "",
        "## Spec 草案",
        "",
        "```yaml",
        dump_yaml(spec).rstrip(),
        "```",
        "",
        "## 提取到的术语/短语（供人工审阅）",
        "",
    ]

    if extracted_terms:
        lines.extend([f"- {t}" for t in extracted_terms])
    else:
        lines.append("- （无）")

    lines.extend(["", "## 规划自检", "", *checks_lines(), ""])
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Plan a NSFC schematic before generating drawio artifacts.")
    p.add_argument("--proposal", type=Path, default=None, help="标书 TEX 文件或目录（目录会自动搜索 *.tex）")
    p.add_argument("--context", type=str, default=None, help="自然语言描述（与 --proposal 二选一）")
    p.add_argument("--plan-md", type=Path, default=None, help="从已有 PLAN.md 中提取 spec 草案并导出 spec_draft.yaml")
    p.add_argument("--output", type=Path, required=True, help="输出目录（会写入 PLAN.md 与 spec_draft.yaml）")
    p.add_argument(
        "--no-workspace-plan",
        action="store_true",
        help="不在当前工作目录额外输出 schematic-plan.md（默认会输出，便于作为交付文件给用户审阅）",
    )
    args = p.parse_args()

    if args.output.exists() and not args.output.is_dir():
        fatal(f"--output 不是目录：{args.output}")

    if args.plan_md is not None:
        if not args.plan_md.exists() or not args.plan_md.is_file():
            fatal(f"--plan-md 不存在或不是文件：{args.plan_md}")
        plan_md = read_text(args.plan_md)
        spec_text = _extract_spec_yaml_from_plan_md(plan_md)
        if not spec_text:
            fatal("未在 PLAN.md 中找到 spec 草案的 YAML fenced code block（```yaml ... ```）")
        spec = _load_yaml_text(spec_text)
        args.output.mkdir(parents=True, exist_ok=True)

        root = skill_root()
        config = load_yaml(root / "config.yaml")
        planning = config.get("planning", {}) if isinstance(config.get("planning"), dict) else {}
        out_cfg = planning.get("output", {}) if isinstance(planning.get("output"), dict) else {}
        spec_name = str(out_cfg.get("spec_filename", "spec_draft.yaml"))

        spec_out = args.output / spec_name
        write_text(spec_out, dump_yaml(spec))
        checks = _run_checks(config, spec)
        worst = "OK"
        order = {"OK": 0, "WARN": 1, "P1": 2, "P0": 3}
        for c in checks:
            worst = c.level if order.get(c.level, 0) > order.get(worst, 0) else worst
        if worst == "P0":
            warn(f"从 PLAN.md 提取的 spec 草案存在 P0 问题（已导出，但建议修正后再进入生成阶段）：{spec_out}")
            raise SystemExit(2)

        info(f"已从 PLAN.md 提取 spec 草案并导出：{spec_out}")
        return

    if bool(args.proposal) == bool(args.context):
        fatal("必须且只能提供其一：--proposal 或 --context（或使用 --plan-md 模式）")

    root = skill_root()
    config = load_yaml(root / "config.yaml")
    planning = config.get("planning", {}) if isinstance(config.get("planning"), dict) else {}
    out_cfg = planning.get("output", {}) if isinstance(planning.get("output"), dict) else {}
    plan_name = str(out_cfg.get("plan_filename", "PLAN.md"))
    spec_name = str(out_cfg.get("spec_filename", "spec_draft.yaml"))
    extraction_cfg = planning.get("extraction", {}) if isinstance(planning.get("extraction"), dict) else {}
    max_terms = int(extraction_cfg.get("max_terms", 12))

    source_label = ""
    extracted_terms: List[str] = []
    used_ai_spec = False

    if args.context:
        source_label = "context"
        # For natural language, treat the whole context as “section text”.
        # We reuse extract_research_terms interface by writing a tiny temp-like path? Keep it simple: just split.
        chunks = re.split(r"[。\n；;]+", args.context)
        extracted_terms = [c.strip() for c in chunks if 2 <= len(c.strip()) <= 36][:max_terms]
    else:
        proposal = args.proposal
        if proposal is None:
            fatal("proposal 为空（内部错误）")
        if not proposal.exists():
            fatal(f"proposal 不存在：{proposal}")
        tex_path = find_candidate_tex(proposal)
        if tex_path is None:
            fatal(f"未在 proposal 中找到可用的 .tex：{proposal}")
        source_label = str(tex_path)
        eval_mode = str((config.get("evaluation", {}) or {}).get("evaluation_mode", "heuristic")).strip().lower()
        if eval_mode == "ai":
            try:
                from ai_extract_tex import AI_TEX_RESPONSE_JSON, consume_tex_extraction, prepare_tex_extraction_request

                args.output.mkdir(parents=True, exist_ok=True)
                req, resp = prepare_tex_extraction_request(tex_path, config=config, output_dir=args.output)
                payload = consume_tex_extraction(resp)
                if payload and isinstance(payload.get("spec_draft"), dict) and payload.get("spec_draft"):
                    spec = payload["spec_draft"]
                    terms = payload.get("terms", [])
                    extracted_terms = [str(t).strip() for t in terms if isinstance(t, (str, int, float)) and str(t).strip()][:max_terms]
                    used_ai_spec = True
                    info(f"已检测到 AI TEX 提取响应：{resp.name}，将直接使用 spec_draft")
                else:
                    info(f"AI TEX 提取协议已生成：{req.name} + {AI_TEX_RESPONSE_JSON}（未检测到有效响应，已降级为正则抽取）")
            except Exception as exc:
                warn(f"AI TEX 提取协议生成/消费失败，已降级为正则抽取（{exc}）")

        if not used_ai_spec:
            extracted_terms = extract_research_terms(tex_path, max_terms=max_terms)
            # Keep a bit more context-derived terms if possible.
            section = extract_research_content_section(tex_path)
            if section and len(extracted_terms) < 6:
                extra = re.split(r"[。\n；;]+", section)
                for c in extra:
                    c = re.sub(r"\\[a-zA-Z]+", " ", c)
                    c = re.sub(r"\$[^$]*\$", " ", c)
                    c = re.sub(r"\s+", " ", c).strip(" ：:;，,")
                    if 6 <= len(c) <= 36 and c not in extracted_terms:
                        extracted_terms.append(c)
                    if len(extracted_terms) >= max_terms:
                        break

    if not used_ai_spec:
        spec = _build_spec_draft(config, extracted_terms)
    checks = _run_checks(config, spec)

    args.output.mkdir(parents=True, exist_ok=True)
    plan_path = args.output / plan_name
    spec_out = args.output / spec_name

    plan_md = _format_plan_md(config, source_label=source_label, extracted_terms=extracted_terms, spec=spec, checks=checks)
    write_text(plan_path, plan_md)
    write_text(spec_out, dump_yaml(spec))
    workspace_plan_written = False
    if not args.no_workspace_plan:
        # Deliverable for humans: keep a stable, flat file in the workspace root for quick review.
        workspace_plan = Path("schematic-plan.md")
        write_text(workspace_plan, plan_md)
        workspace_plan_written = True

    worst = "OK"
    order = {"OK": 0, "WARN": 1, "P1": 2, "P0": 3}
    for c in checks:
        worst = c.level if order.get(c.level, 0) > order.get(worst, 0) else worst

    if worst in {"P0"}:
        warn(f"规划自检存在 P0 问题：已输出草案，但建议先修正后再进入生成阶段。输出目录：{args.output}")
        # Keep outputs, but fail fast so CI/用户不会误用不合格规划进入后续渲染。
        raise SystemExit(2)

    if not workspace_plan_written:
        info(f"完成：{plan_path} + {spec_out}")
    else:
        info(f"完成：{plan_path} + {spec_out} + schematic-plan.md")


if __name__ == "__main__":
    main()
