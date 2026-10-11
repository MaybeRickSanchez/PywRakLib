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


class IncompatibleProtocolVersion(OfflineMessage):
    ID = MessageIdentifiers.ID_INCOMPATIBLE_PROTOCOL_VERSION

    def __init__(self):
        super().__init__()
        self.protocolVersion: int = 0
        self.serverId: int = 0

    @staticmethod
    def create(protocolVersion: int, serverId: int) -> "IncompatibleProtocolVersion":
        result = IncompatibleProtocolVersion()
        result.protocolVersion = protocolVersion
        result.serverId = serverId
        return result

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putByte(self.protocolVersion)
        self.writeMagic(out)
        out.putLong(self.serverId)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.protocolVersion = in_.getByte()
        self.readMagic(in_)
        self.serverId = in_.getLong()