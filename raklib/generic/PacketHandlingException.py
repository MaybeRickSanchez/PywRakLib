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

"""Raised when a packet cannot be handled, carrying a reason to use when disconnecting the peer."""

from __future__ import annotations


class PacketHandlingException(RuntimeError):
    def __init__(self, message: str, disconnectReason: int, code: int = 0, previous: BaseException | None = None):
        super().__init__(message)
        self._disconnectReason = disconnectReason
        self._code = code
        self._previous = previous

    def getDisconnectReason(self) -> int:
        return self._disconnectReason

    @property
    def code(self) -> int:
        return self._code