# This file is part of PywRakLib.
# Copyright (C) 2014-2022 PocketMine Team <https://github.com/pmmp/RakLib>
# Copyright (C) 2026 Amirreza Prime <https://github.com/MaybeRickSanchez/PywRakLib>
#
# PywRakLib is an unofficial Python port of RakLib.
# RakLib is not affiliated with Jenkins Software LLC nor RakNet.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
A minimal logging facility mirroring the ``pocketmine/log`` package that RakLib depends on.

The upstream package provides ``Logger``, ``PrefixedLogger``, ``BufferedLogger`` and the ``GlobalLogger`` singleton.
Only the subset of functionality used by RakLib is implemented here.
"""

from __future__ import annotations

import sys
import threading
import traceback
from typing import Callable, Optional, TextIO


class LogLevel:
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7

    _NAMES = {
        EMERGENCY: "emergency",
        ALERT: "alert",
        CRITICAL: "critical",
        ERROR: "error",
        WARNING: "warning",
        NOTICE: "notice",
        INFO: "info",
        DEBUG: "debug",
    }

    @classmethod
    def name(cls, level: int) -> str:
        return cls._NAMES.get(level, f"level({level})")


_FATAL_LEVEL = LogLevel.EMERGENCY
_DEFAULT_THRESHOLD = LogLevel.INFO


class Logger:
    """Base logger. Subclasses are expected to override :meth:`log`."""

    def __init__(self, level: int = _DEFAULT_THRESHOLD):
        self.level = level

    def emergency(self, message: str) -> None:
        self.log(LogLevel.EMERGENCY, message)

    def alert(self, message: str) -> None:
        self.log(LogLevel.ALERT, message)

    def critical(self, message: str) -> None:
        self.log(LogLevel.CRITICAL, message)

    def error(self, message: str) -> None:
        self.log(LogLevel.ERROR, message)

    def warning(self, message: str) -> None:
        self.log(LogLevel.WARNING, message)

    def notice(self, message: str) -> None:
        self.log(LogLevel.NOTICE, message)

    def info(self, message: str) -> None:
        self.log(LogLevel.INFO, message)

    def debug(self, message: str) -> None:
        self.log(LogLevel.DEBUG, message)

    def logException(self, exception: BaseException, trace: Optional[list] = None) -> None:
        if trace is None:
            trace = traceback.format_exception(type(exception), exception, exception.__traceback__)
        self.critical("".join(trace).rstrip("\n"))

    def log(self, level: int, message: str) -> None:
        raise NotImplementedError


class StandardLogger(Logger):
    """Writes log messages to a stream (stderr by default)."""

    def __init__(self, level: int = _DEFAULT_THRESHOLD, stream: Optional[TextIO] = None):
        super().__init__(level)
        self._stream = stream if stream is not None else sys.stderr
        self._lock = threading.Lock()

    def log(self, level: int, message: str) -> None:
        if level > self.level:
            return
        with self._lock:
            self._stream.write(f"{LogLevel.name(level)}: {message}\n")
            self._stream.flush()


class PrefixedLogger(Logger):
    """Wraps another logger, prepending a fixed prefix to every message."""

    def __init__(self, logger: Logger, prefix: str):
        super().__init__(logger.level)
        self._logger = logger
        self._prefix = prefix

    @property
    def level(self) -> int:
        return self._logger.level

    @level.setter
    def level(self, value: int) -> None:
        if hasattr(self, "_logger"):
            self._logger.level = value

    def log(self, level: int, message: str) -> None:
        self._logger.log(level, f"[{self._prefix}] {message}")


class BufferedLogger(Logger):
    """Defers log output until :meth:`flush` is called, batching writes for performance."""

    def __init__(self, logger: Logger):
        super().__init__(logger.level)
        self._logger = logger
        self._buffer: list[str] = []
        self._buffering = False

    @property
    def level(self) -> int:
        return self._logger.level

    @level.setter
    def level(self, value: int) -> None:
        if hasattr(self, "_logger"):
            self._logger.level = value

    def log(self, level: int, message: str) -> None:
        if self._buffering:
            self._buffer.append(message)
        else:
            self._logger.log(level, message)

    def buffer(self, callback: Callable[[], None]) -> None:
        self._buffering = True
        try:
            callback()
        finally:
            self._buffering = False
            self.flush()

    def flush(self) -> None:
        for message in self._buffer:
            self._logger.log(LogLevel.DEBUG, message)
        self._buffer = []


class GlobalLogger(StandardLogger):
    """Singleton logger used as the default by the tools/scripts."""

    _instance: Optional["GlobalLogger"] = None

    def __init__(self):
        super().__init__(LogLevel.DEBUG)

    @classmethod
    def get(cls) -> "GlobalLogger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance