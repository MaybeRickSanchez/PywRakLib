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

"""Interface for listening to server events."""

from __future__ import annotations


class ServerEventListener:
    def onClientConnect(self, sessionId: int, address: str, port: int, clientID: int) -> None:
        raise NotImplementedError

    def onClientDisconnect(self, sessionId: int, reason: int) -> None:
        """reason is one of the DisconnectReason constants."""
        raise NotImplementedError

    def onPacketReceive(self, sessionId: int, packet: bytes) -> None:
        raise NotImplementedError

    def onRawPacketReceive(self, address: str, port: int, payload: bytes) -> None:
        raise NotImplementedError

    def onPacketAck(self, sessionId: int, identifierACK: int) -> None:
        raise NotImplementedError

    def onBandwidthStatsUpdate(self, bytesSentDiff: int, bytesReceivedDiff: int) -> None:
        raise NotImplementedError

    def onPingMeasure(self, sessionId: int, pingMS: int) -> None:
        raise NotImplementedError