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


class OpenConnectionReply1(OfflineMessage):
    ID = MessageIdentifiers.ID_OPEN_CONNECTION_REPLY_1

    def __init__(self):
        super().__init__()
        self.serverID: int = 0
        self.cookie: int | None = None
        self.mtuSize: int = 0

    @staticmethod
    def create(serverId: int, cookie: int | None, mtuSize: int) -> "OpenConnectionReply1":
        result = OpenConnectionReply1()
        result.serverID = serverId
        result.cookie = cookie
        result.mtuSize = mtuSize
        return result

    def encodePayload(self, out: PacketSerializer) -> None:
        self.writeMagic(out)
        out.putLong(self.serverID)
        if self.cookie is not None:
            out.putByte(1)
            out.putInt(self.cookie)
            # TODO: If the client supports libcat security, we're expected to send a public key here.
            # However this would require context-specific logic and I really cba with it
        else:
            out.putByte(0)
        out.putShort(self.mtuSize)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.readMagic(in_)
        self.serverID = in_.getLong()
        if in_.getByte() != 0:
            self.cookie = in_.getInt()
            # TODO: If the server supports libcat security, it'll send a public key here.
        else:
            self.cookie = None
        self.mtuSize = in_.getShort()