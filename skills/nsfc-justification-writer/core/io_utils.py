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
    except Exception:
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


def iter_text_chunks_by_subsubsection_mark(
    path: Path,
    *,
    encoding: str = "utf-8",
    errors: str = "ignore",
    max_chars: int,
    max_chunks: int,
) -> Iterator[str]:
    """
    近似按 \\subsubsection{...} 边界进行分块的流式读取：
    - 适用于 Tier2 等“只需要近似块边界”的场景
    - 不保证严格 LaTeX 语法正确性，但可避免一次性加载超大文件
    """
    p = Path(path).resolve()
    if max_chars <= 0:
        yield read_text_streaming(p, encoding=encoding, errors=errors).text
        return

    buf = ""
    produced = 0
    mark = "\\subsubsection{"

    with p.open("r", encoding=encoding, errors=errors) as f:
        for line in f:
            if produced >= max_chunks:
                break
            # 若已接近上限且下一行包含 mark，则优先在 mark 前切块
            if (len(buf) >= max_chars) and (mark in line):
                idx = line.find(mark)
                head = line[:idx]
                tail = line[idx:]
                if head:
                    if len(buf) + len(head) > max_chars:
                        yield buf
                        produced += 1
                        buf = ""
                    buf += head
                if buf.strip():
                    yield buf
                    produced += 1
                buf = tail
                continue

            if len(buf) + len(line) > max_chars and buf:
                yield buf
                produced += 1
                buf = ""
                if produced >= max_chunks:
                    break
            buf += line

    if produced < max_chunks and buf.strip():
        yield buf
