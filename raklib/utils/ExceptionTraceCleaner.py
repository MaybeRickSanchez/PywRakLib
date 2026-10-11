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

"""Cleans up stack traces for logging, ported from RakLib's ``ExceptionTraceCleaner``."""

from __future__ import annotations

import traceback


class ExceptionTraceCleaner:
    def __init__(self, mainPath: str):
        self.mainPath = mainPath

    def getTrace(self, start: int = 0, trace=None) -> list[str]:
        """
        Formats a stack trace into a list of human-readable lines.

        :param start: index of the first frame to include
        :param trace: a pre-computed trace, or None to capture the current one.
        """
        if trace is None:
            trace = traceback.extract_stack()[:-1]

        messages: list[str] = []
        for j, frame in enumerate(trace[start:]):
            params = ",".join(str(value) for value in getattr(frame, "locals", {}).values()) if hasattr(frame, "locals") else ""
            messages.append(
                f"#{j} {self.cleanPath(frame.filename)}({frame.lineno}): {frame.name}({params})"
            )

        return messages

    def cleanPath(self, path: str) -> str:
        return (
            path.replace("\\", "/")
            .replace(".py", "")
            .replace("phar://", "")
            .replace(self.mainPath.replace("\\", "/").replace("phar://", ""), "")
        )