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


class ConnectionRequest(ConnectedPacket):
    ID = MessageIdentifiers.ID_CONNECTION_REQUEST

    def __init__(self):
        self.clientID: int = 0
        self.sendPingTime: int = 0
        self.useSecurity: bool = False

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putLong(self.clientID)
        out.putLong(self.sendPingTime)
        out.putByte(1 if self.useSecurity else 0)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.clientID = in_.getLong()
        self.sendPingTime = in_.getLong()
        self.useSecurity = in_.getByte() != 0