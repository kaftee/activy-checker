"""A small terminal spinner for long-running steps.

It writes to stderr and only animates when stderr is a terminal, so piping or
redirecting the report (``activy-checker > report.txt``) stays clean.
"""
from __future__ import annotations

import shutil
import sys
import threading
from typing import TextIO

FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Spinner:
    """Context manager showing ``<frame> <message>`` on one self-updating line.

    >>> with Spinner("Working") as sp:
    ...     sp.update("Still working")
    """

    def __init__(self, message: str = "", stream: TextIO | None = None,
                 interval: float = 0.1, enabled: bool | None = None):
        self.stream = stream or sys.stderr
        if enabled is None:
            isatty = getattr(self.stream, "isatty", None)
            enabled = bool(isatty and isatty())
        self.enabled = enabled
        self.message = message
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._frame = 0

    def update(self, message: str) -> None:
        self.message = message

    def start(self) -> "Spinner":
        if self.enabled and self._thread is None:
            self._draw()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def stop(self, final: str | None = None) -> None:
        """Stop animating and clear the line; optionally print ``final`` instead."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
            self._thread = None
            with self._lock:
                self.stream.write("\r" + " " * self._width() + "\r")
                self.stream.flush()
        if final is not None and self.enabled:
            self.stream.write(final + "\n")
            self.stream.flush()

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # ---- internals -------------------------------------------------------
    def _width(self) -> int:
        return max(20, shutil.get_terminal_size((80, 20)).columns - 1)

    def _draw(self) -> None:
        with self._lock:
            frame = FRAMES[self._frame % len(FRAMES)]
            self._frame += 1
            text = f"{frame} {self.message}"[: self._width()]
            self.stream.write("\r" + text.ljust(self._width()))
            self.stream.flush()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self._draw()
