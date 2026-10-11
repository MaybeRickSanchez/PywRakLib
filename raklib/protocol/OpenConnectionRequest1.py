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

from raklib.RakLib import RakLib
from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.Packet import OfflineMessage
from raklib.protocol.PacketSerializer import PacketSerializer


class OpenConnectionRequest1(OfflineMessage):
    ID = MessageIdentifiers.ID_OPEN_CONNECTION_REQUEST_1

    def __init__(self):
        super().__init__()
        self.protocol: int = RakLib.DEFAULT_PROTOCOL_VERSION
        self.mtuSize: int = 0

    def encodePayload(self, out: PacketSerializer) -> None:
        self.writeMagic(out)
        out.putByte(self.protocol)
        out.put(b"\x00" * (self.mtuSize - len(out.getBuffer())))

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.readMagic(in_)
        self.protocol = in_.getByte()
        self.mtuSize = len(in_.getBuffer())
        in_.getRemaining()  # silence unread warnings