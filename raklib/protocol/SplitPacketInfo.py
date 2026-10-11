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

"""Information about a split (fragmented) packet, ported from RakLib's ``SplitPacketInfo``."""

from __future__ import annotations


class SplitPacketInfo:
    __slots__ = ("_id", "_partIndex", "_totalPartCount")

    def __init__(self, id: int, partIndex: int, totalPartCount: int):
        self._id = id
        self._partIndex = partIndex
        self._totalPartCount = totalPartCount

    def getId(self) -> int:
        return self._id

    def getPartIndex(self) -> int:
        return self._partIndex

    def getTotalPartCount(self) -> int:
        return self._totalPartCount