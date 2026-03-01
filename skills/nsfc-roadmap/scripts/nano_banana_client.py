from __future__ import annotations

import base64
import json
import math
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from env_utils import find_dotenv, mask_secret, merged_env
from utils import fatal, info, warn


@dataclass(frozen=True)
class GeminiConfig:
    base_url: str
    api_key: str
    model: str
    dotenv_path: Optional[Path]


class GeminiHTTPError(RuntimeError):
    def __init__(self, code: int, reason: str, detail: str):
        super().__init__(f"HTTP {code} {reason}: {detail}")
        self.code = int(code)
        self.reason = str(reason)
        self.detail = str(detail)


def load_gemini_config(*, dotenv_path: Optional[Path] = None, search_from: Optional[Path] = None) -> GeminiConfig:
    """
    Load Gemini config from user's `.env` (preferred) and environment variables (override).

    Expected variables (any of the following):
    - GEMINI_BASE_URL (e.g. https://generativelanguage.googleapis.com/v1beta)
    - GEMINI_API / GEMINI_API_KEY / GOOGLE_API_KEY
    - GEMINI_MODEL (e.g. gemini-3.1-flash-image-preview)
    """
    if dotenv_path is None:
        start = (search_from or Path.cwd()).resolve()
        dotenv_path = find_dotenv(start)

    env = merged_env(dotenv_path=dotenv_path)

    base_url = str(env.get("GEMINI_BASE_URL", "") or "").strip()
    api_key = str(env.get("GEMINI_API_KEY", "") or env.get("GEMINI_API", "") or env.get("GOOGLE_API_KEY", "") or "").strip()
    model = str(env.get("GEMINI_MODEL", "") or "").strip()

    missing: List[str] = []
    if not base_url:
        missing.append("GEMINI_BASE_URL")
    if not api_key:
        missing.append("GEMINI_API / GEMINI_API_KEY / GOOGLE_API_KEY")
    if not model:
        missing.append("GEMINI_MODEL")
    if missing:
        hint = "，".join(missing)
        fatal(
            "未检测到 Gemini 配置（缺少：{}）。\n"
            "请在项目根目录 `.env` 或系统环境变量中配置 Gemini：\n"
            "- GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta\n"
            "- GEMINI_API=你的 API Key\n"
            "- GEMINI_MODEL=gemini-3.1-flash-image-preview\n".format(hint)
        )

    base_url = base_url.rstrip("/")
    return GeminiConfig(base_url=base_url, api_key=api_key, model=model, dotenv_path=dotenv_path)


def _post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout_s: int = 60,
) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            detail = raw.decode("utf-8", errors="replace")
        except Exception:
            detail = str(raw)
        raise GeminiHTTPError(int(exc.code), str(exc.reason), detail[:1200]) from exc
    except Exception as exc:
        raise RuntimeError(f"请求失败：{exc}") from exc

    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"响应 JSON 解析失败：{exc}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError("响应不是 JSON object")
    return obj


def generate_content(cfg: GeminiConfig, payload: Dict[str, Any], *, timeout_s: int = 120) -> Dict[str, Any]:
    """
    Call Gemini REST API: models.generateContent

    Prefer header-based auth (`x-goog-api-key`) to avoid leaking keys into URLs/logs.
    Some third-party proxies may not support this header; we fallback to `?key=...` once.
    """
    endpoint = f"{cfg.base_url}/models/{cfg.model}:generateContent"
    headers = {"x-goog-api-key": cfg.api_key}
    try:
        return _post_json(endpoint, payload, headers=headers, timeout_s=timeout_s)
    except GeminiHTTPError as exc:
        # Fallback: only for auth-related failures; do NOT retry on 4xx payload errors.
        if exc.code not in {401, 403}:
            raise
        warn(f"Gemini header 认证失败（HTTP {exc.code}），尝试回退到 query key（可能是代理网关限制）。")
        endpoint2 = f"{endpoint}?key={cfg.api_key}"
        return _post_json(endpoint2, payload, headers=None, timeout_s=timeout_s)


def nano_banana_health_check(
    *,
    dotenv_path: Optional[Path] = None,
    search_from: Optional[Path] = None,
    timeout_s: int = 30,
) -> GeminiConfig:
    """
    Validate that user's `.env` Gemini config can reach the model.
    """
    cfg = load_gemini_config(dotenv_path=dotenv_path, search_from=search_from)
    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
        "generationConfig": {"responseModalities": ["TEXT"], "maxOutputTokens": 16, "temperature": 0.0},
    }
    resp = generate_content(cfg, payload, timeout_s=timeout_s)
    if not isinstance(resp.get("candidates"), list) or not resp.get("candidates"):
        raise RuntimeError("响应缺少 candidates，疑似模型不可用或返回结构异常。")
    info(
        "Nano Banana(Gemini) 连通性检查通过："
        f"model={cfg.model}, base_url={cfg.base_url}, api_key={mask_secret(cfg.api_key)}"
    )
    return cfg


def _extract_inline_images(resp: Dict[str, Any]) -> List[Tuple[str, bytes]]:
    """
    Extract image bytes from candidates[].content.parts[] inline data.
    Be tolerant to both snake_case (inline_data) and camelCase (inlineData).
    """
    out: List[Tuple[str, bytes]] = []

    candidates = resp.get("candidates")
    if not isinstance(candidates, list):
        return out

    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        content = cand.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get("inline_data") or part.get("inlineData")
            if not isinstance(inline, dict):
                continue
            mime = str(inline.get("mime_type") or inline.get("mimeType") or "").strip().lower()
            data_b64 = inline.get("data")
            if not isinstance(data_b64, str) or not data_b64.strip():
                continue
            try:
                raw = base64.b64decode(data_b64)
            except Exception:
                continue
            if not mime:
                mime = "application/octet-stream"
            out.append((mime, raw))
    return out


def _best_image(images: List[Tuple[str, bytes]]) -> Optional[Tuple[str, bytes]]:
    if not images:
        return None
    # Prefer PNG; then by size.
    scored: List[Tuple[int, int, Tuple[str, bytes]]] = []
    for mime, raw in images:
        png_bonus = 1 if ("png" in mime) else 0
        scored.append((png_bonus, len(raw), (mime, raw)))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]


def _choose_aspect_ratio(w: int, h: int) -> str:
    """
    Gemini imageConfig supports a finite set of aspect ratios.
    Pick the closest one for the requested canvas.
    """
    ratios = {
        "16:9": 16 / 9,
        "9:16": 9 / 16,
        "4:3": 4 / 3,
        "3:4": 3 / 4,
        "3:2": 3 / 2,
        "2:3": 2 / 3,
        "1:1": 1.0,
        "5:4": 5 / 4,
        "4:5": 4 / 5,
        "21:9": 21 / 9,
        "1:4": 1 / 4,
        "4:1": 4 / 1,
        "1:8": 1 / 8,
        "8:1": 8 / 1,
    }
    target = (w / max(1, h)) if h else 1.0
    best = min(ratios.items(), key=lambda kv: abs(kv[1] - target))
    return best[0]


def _choose_image_size(w: int, h: int) -> str:
    m = max(int(w), int(h))
    if m >= 2600:
        return "IMAGE_SIZE_4K"
    if m >= 1400:
        return "IMAGE_SIZE_2K"
    return "IMAGE_SIZE_1K"


def _maybe_resize_to_canvas(png_path: Path, *, target_w: int, target_h: int) -> None:
    """
    Ensure the exported PNG is high-resolution and matches the target canvas size.
    Uses Pillow if available; otherwise keep original.
    """
    try:
        from PIL import Image  # type: ignore
    except Exception:
        warn("缺少 Pillow，无法对 Nano Banana 输出 PNG 做尺寸对齐（已跳过）。")
        return

    try:
        with Image.open(png_path) as img:
            w, h = img.size
            if w == target_w and h == target_h:
                return
            # Fit-with-padding (contain): preserve all content, avoid cropping.
            scale = min(target_w / max(1, w), target_h / max(1, h))
            new_w = max(1, int(math.floor(w * scale)))
            new_h = max(1, int(math.floor(h * scale)))
            resized = img.convert("RGBA").resize((new_w, new_h), resample=Image.LANCZOS)
            canvas = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 255))
            ox = (target_w - new_w) // 2
            oy = (target_h - new_h) // 2
            canvas.paste(resized, (ox, oy), resized)
            canvas.convert("RGB").save(png_path, format="PNG", optimize=True)
    except Exception as exc:
        warn(f"PNG 尺寸对齐失败（已忽略）：{exc}")


def nano_banana_generate_png(
    *,
    cfg: GeminiConfig,
    prompt: str,
    output_png: Path,
    canvas_w: int,
    canvas_h: int,
    debug_dir: Optional[Path] = None,
    timeout_s: int = 180,
) -> None:
    """
    Generate a PNG image with Nano Banana (Gemini image model).
    Writes:
    - output_png: final PNG (best-effort resized to canvas_w/canvas_h)
    - debug_dir/nano_banana_response.json: response (no API key)
    """
    aspect = _choose_aspect_ratio(canvas_w, canvas_h)
    size = _choose_image_size(canvas_w, canvas_h)

    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "temperature": 0.2,
            "imageConfig": {"aspectRatio": aspect, "imageSize": size},
        },
    }
    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "nano_banana_request.json").write_text(
            json.dumps(
                {
                    "base_url": cfg.base_url,
                    "model": cfg.model,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def parse_retry_after_s(detail: str) -> Optional[float]:
        m = re.search(r"retry\\s+in\\s+([0-9]+(?:\\.[0-9]+)?)s", detail, flags=re.IGNORECASE)
        if not m:
            return None
        try:
            return float(m.group(1))
        except Exception:
            return None

    attempts = 0
    last_err: Optional[Exception] = None
    while attempts < 5:
        attempts += 1
        try:
            resp = generate_content(cfg, payload, timeout_s=timeout_s)
            last_err = None
            break
        except GeminiHTTPError as exc:
            last_err = exc
            if exc.code not in {429, 503}:
                raise
            wait_s = parse_retry_after_s(exc.detail) or min(30.0, 2.0**attempts)
            warn(f"Gemini 暂时限流/资源耗尽（HTTP {exc.code}），{wait_s:.1f}s 后重试（{attempts}/5）...")
            time.sleep(max(0.5, float(wait_s)))
    else:
        resp = {}

    if last_err is not None:
        raise last_err

    if debug_dir is not None:
        (debug_dir / "nano_banana_response.json").write_text(
            json.dumps(resp, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    images = _extract_inline_images(resp)
    best = _best_image(images)
    if best is None:
        excerpt = json.dumps(resp, ensure_ascii=False)[:800]
        raise RuntimeError(f"未从 Gemini 响应中提取到图片（inline_data）。response_excerpt={excerpt}")
    mime, raw = best
    if "png" not in mime:
        warn(f"Gemini 返回图片 mime 不是 PNG（{mime}），仍将按 PNG 写出（若无法打开请检查响应）。")

    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_png.write_bytes(raw)
    _maybe_resize_to_canvas(output_png, target_w=int(canvas_w), target_h=int(canvas_h))

