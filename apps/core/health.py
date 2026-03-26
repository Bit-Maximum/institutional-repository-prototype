from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Any


@dataclass
class _StartupState:
    warmup_enabled: bool = False
    warmup_started: bool = False
    warmup_completed: bool = False
    warmup_failed: bool = False
    ready_logged: bool = False
    last_error: str = ""
    updated_at: float = field(default_factory=time)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def configure(self, *, warmup_enabled: bool) -> None:
        with self._lock:
            self.warmup_enabled = bool(warmup_enabled)
            self.updated_at = time()

    def mark_warmup_started(self) -> None:
        with self._lock:
            self.warmup_started = True
            self.warmup_completed = False
            self.warmup_failed = False
            self.last_error = ""
            self.updated_at = time()

    def mark_warmup_completed(self) -> None:
        with self._lock:
            self.warmup_started = True
            self.warmup_completed = True
            self.warmup_failed = False
            self.last_error = ""
            self.updated_at = time()

    def mark_warmup_failed(self, message: str) -> None:
        with self._lock:
            self.warmup_started = True
            self.warmup_completed = False
            self.warmup_failed = True
            self.last_error = str(message)
            self.updated_at = time()

    def mark_ready_logged(self) -> bool:
        with self._lock:
            already_logged = self.ready_logged
            self.ready_logged = True
            self.updated_at = time()
            return already_logged

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "warmup_enabled": self.warmup_enabled,
                "warmup_started": self.warmup_started,
                "warmup_completed": self.warmup_completed,
                "warmup_failed": self.warmup_failed,
                "last_error": self.last_error,
                "updated_at": self.updated_at,
            }


startup_state = _StartupState()
