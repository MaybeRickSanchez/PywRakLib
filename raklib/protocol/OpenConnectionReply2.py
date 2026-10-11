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
from raklib.utils.InternetAddress import InternetAddress


class OpenConnectionReply2(OfflineMessage):
    ID = MessageIdentifiers.ID_OPEN_CONNECTION_REPLY_2

    def __init__(self):
        super().__init__()
        self.serverID: int = 0
        self.clientAddress: InternetAddress = InternetAddress("0.0.0.0", 0, 4)
        self.mtuSize: int = 0
        self.serverSecurity: bool = False

    @staticmethod
    def create(
        serverId: int,
        clientAddress: InternetAddress,
        mtuSize: int,
        serverSecurity: bool,
    ) -> "OpenConnectionReply2":
        result = OpenConnectionReply2()
        result.serverID = serverId
        result.clientAddress = clientAddress
        result.mtuSize = mtuSize
        result.serverSecurity = serverSecurity
        return result

    def encodePayload(self, out: PacketSerializer) -> None:
        self.writeMagic(out)
        out.putLong(self.serverID)
        out.putAddress(self.clientAddress)
        out.putShort(self.mtuSize)
        out.putByte(1 if self.serverSecurity else 0)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.readMagic(in_)
        self.serverID = in_.getLong()
        self.clientAddress = in_.getAddress()
        self.mtuSize = in_.getShort()
        self.serverSecurity = in_.getByte() != 0