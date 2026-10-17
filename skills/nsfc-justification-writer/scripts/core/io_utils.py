#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass(frozen=True)
class ReadTextResult:
    text: str
    truncated: bool
    bytes_read: int
    total_bytes: int


def read_text_streaming(
    path: Path,
    *,
    encoding: str = "utf-8",
    errors: str = "ignore",
    max_bytes: Optional[int] = None,
    chunk_size: int = 1024 * 1024,
) -> ReadTextResult:
    """
    以流式方式读取文本，避免一次性 read() 带来的峰值内存。

    - max_bytes=None：读取全文件（仍会返回完整字符串，但读取过程为流式）
    - max_bytes=int：最多读取指定字节数（用于超大文件场景的“保底可用”）
    """
    p = Path(path).resolve()
    try:
        total = int(p.stat().st_size)
    except OSError:
        total = 0

    decoder = codecs.getincrementaldecoder(encoding)(errors=errors)
    parts: list[str] = []
    bytes_read = 0
    truncated = False

    with p.open("rb") as f:
        while True:
            if max_bytes is not None and bytes_read >= max_bytes:
                truncated = True
                break
            to_read = chunk_size
            if max_bytes is not None:
                to_read = min(to_read, max_bytes - bytes_read)
            b = f.read(to_read)
            if not b:
                break
            bytes_read += len(b)
            parts.append(decoder.decode(b))

    parts.append(decoder.decode(b"", final=True))
    return ReadTextResult(text="".join(parts), truncated=truncated, bytes_read=bytes_read, total_bytes=total)


def iter_text_chunks_by_paragraph(
    path: Path,
    *,
    encoding: str = "utf-8",
    errors: str = "ignore",
    max_chars: int,
    max_chunks: int,
) -> Iterator[str]:
    """按空行/字符上限流式分块；不依赖任何 LaTeX 标题宏。"""
    p = Path(path).resolve()
    if max_chars <= 0:
        yield read_text_streaming(p, encoding=encoding, errors=errors).text
        return
    buf = ""
    produced = 0
    with p.open("r", encoding=encoding, errors=errors) as f:
        for line in f:
            if produced >= max_chunks:
                break
            buf += line
            if len(buf) >= max_chars or (not line.strip() and len(buf) >= max_chars // 2):
                yield buf
                produced += 1
                buf = ""
        if buf and produced < max_chunks:
            yield buf
