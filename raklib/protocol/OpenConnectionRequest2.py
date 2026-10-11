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
from raklib.utils.binary import Binary
from raklib.utils.InternetAddress import InternetAddress


class OpenConnectionRequest2(OfflineMessage):
    ID = MessageIdentifiers.ID_OPEN_CONNECTION_REQUEST_2

    TAIL_FIELDS_SIZE_COMMON = 2 + 8  # mtu + client ID
    TAIL_FIELDS_SIZE_IPV4 = TAIL_FIELDS_SIZE_COMMON + PacketSerializer.IPV4_SIZE
    TAIL_FIELDS_SIZE_IPV6 = TAIL_FIELDS_SIZE_COMMON + PacketSerializer.IPV6_SIZE

    def __init__(self):
        super().__init__()
        self.clientID: int = 0
        self.serverAddress: InternetAddress = InternetAddress("0.0.0.0", 0, 4)
        self.cookie: int | None = None
        self.mtuSize: int = 0

    def encodePayload(self, out: PacketSerializer) -> None:
        self.writeMagic(out)
        if self.cookie is not None:
            out.putInt(self.cookie)
            # TODO: encryption challenge - not supported for now because RakNet sucks and we don't need it
            out.putByte(0)
        out.putAddress(self.serverAddress)
        out.putShort(self.mtuSize)
        out.putLong(self.clientID)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.readMagic(in_)

        remaining = len(in_.getBuffer()) - in_.getOffset()
        if remaining != self.TAIL_FIELDS_SIZE_IPV4 and remaining != self.TAIL_FIELDS_SIZE_IPV6:
            self.cookie = in_.getInt()
            if self.cookie < 0:
                # BinaryStream moment
                self.cookie = Binary.unsignInt(self.cookie)
            # TODO: encryption challenge - not supported for now because RakNet sucks and we don't need it
            # we could handle this by looking at the remaining length of the packet, but it's not worth the complexity
            in_.getByte()
        self.serverAddress = in_.getAddress()
        self.mtuSize = in_.getShort()
        self.clientID = in_.getLong()