#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


class NSFCJustificationWriterError(Exception):
    pass


class MissingCitationKeysError(NSFCJustificationWriterError):
    def __init__(self, missing_keys: list[str]) -> None:
        self.missing_keys = missing_keys
        super().__init__(f"missing citation keys: {', '.join(missing_keys)}")


class BackupNotFoundError(NSFCJustificationWriterError):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"backup not found for run_id={run_id}")

