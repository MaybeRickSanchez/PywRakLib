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

"""Cache entry for reliable packets awaiting acknowledgement."""

from __future__ import annotations

import time

from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket


class ReliableCacheEntry:
    def __init__(self, packets: list[EncapsulatedPacket]):
        self._packets = packets
        self._timestamp = time.time()

    def getPackets(self) -> list[EncapsulatedPacket]:
        return self._packets

    def getTimestamp(self) -> float:
        return self._timestamp