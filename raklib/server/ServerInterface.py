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

"""Interface implemented by the server, exposed to event sources/handlers."""

from __future__ import annotations

from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket


class ServerInterface:
    def sendEncapsulated(self, sessionId: int, packet: EncapsulatedPacket, immediate: bool = False) -> None:
        raise NotImplementedError

    def sendRaw(self, address: str, port: int, payload: bytes) -> None:
        raise NotImplementedError

    def closeSession(self, sessionId: int) -> None:
        raise NotImplementedError

    def setName(self, name: str) -> None:
        raise NotImplementedError

    def setPortCheck(self, value: bool) -> None:
        raise NotImplementedError

    def setPacketsPerTickLimit(self, limit: int) -> None:
        raise NotImplementedError

    def blockAddress(self, address: str, timeout: int) -> None:
        raise NotImplementedError

    def unblockAddress(self, address: str) -> None:
        raise NotImplementedError

    def addRawPacketFilter(self, regex: str) -> None:
        raise NotImplementedError