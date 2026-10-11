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
from raklib.protocol.Packet import ConnectedPacket
from raklib.protocol.PacketSerializer import PacketSerializer


class ConnectedPong(ConnectedPacket):
    ID = MessageIdentifiers.ID_CONNECTED_PONG

    def __init__(self):
        self.sendPingTime: int = 0
        self.sendPongTime: int = 0

    @staticmethod
    def create(sendPingTime: int, sendPongTime: int) -> "ConnectedPong":
        result = ConnectedPong()
        result.sendPingTime = sendPingTime
        result.sendPongTime = sendPongTime
        return result

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putLong(self.sendPingTime)
        out.putLong(self.sendPongTime)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.sendPingTime = in_.getLong()
        self.sendPongTime = in_.getLong()