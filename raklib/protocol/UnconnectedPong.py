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

from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.Packet import OfflineMessage
from raklib.protocol.PacketSerializer import PacketSerializer


class UnconnectedPong(OfflineMessage):
    ID = MessageIdentifiers.ID_UNCONNECTED_PONG

    def __init__(self):
        super().__init__()
        self.sendPingTime: int = 0
        self.serverId: int = 0
        self.serverName: bytes = b""

    @staticmethod
    def create(sendPingTime: int, serverId: int, serverName: bytes) -> "UnconnectedPong":
        result = UnconnectedPong()
        result.sendPingTime = sendPingTime
        result.serverId = serverId
        result.serverName = serverName
        return result

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putLong(self.sendPingTime)
        out.putLong(self.serverId)
        self.writeMagic(out)
        out.putString(self.serverName)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.sendPingTime = in_.getLong()
        self.serverId = in_.getLong()
        self.readMagic(in_)
        self.serverName = in_.getString()