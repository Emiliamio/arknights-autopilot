# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Global Abort Sentinel & Emergency Stop Controller
Author: Emiliamio <mio2110767128@163.com>
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger("ASTA.AbortController")


class AbortController:
    """
    Thread-safe global emergency stop coordinator.
    Signals all long-running execution loops (combat, navigation, cruiser, launcher)
    to halt immediately.
    """

    _abort_event = threading.Event()
    _reason: str = ""
    _lock = threading.Lock()

    @classmethod
    def trigger_abort(cls, reason: str = "用户触发全局紧急停止") -> None:
        """Triggers emergency stop signal across the entire system."""
        with cls._lock:
            cls._reason = reason
            cls._abort_event.set()
        logger.warning(f"🛑 [AbortController] EMERGENCY STOP TRIGGERED: {reason}")

    @classmethod
    def is_aborted(cls) -> bool:
        """Check if emergency stop signal has been tripped."""
        return cls._abort_event.is_set()

    @classmethod
    def get_reason(cls) -> str:
        with cls._lock:
            return cls._reason

    @classmethod
    def reset(cls) -> None:
        """Clears abort flag to allow new tasks to execute."""
        with cls._lock:
            cls._abort_event.clear()
            cls._reason = ""
        logger.info("🟢 [AbortController] Emergency stop flag cleared. System armed.")
