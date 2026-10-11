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
from raklib.protocol.Packet import ConnectedPacket
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.utils.InternetAddress import InternetAddress


class NewIncomingConnection(ConnectedPacket):
    ID = MessageIdentifiers.ID_NEW_INCOMING_CONNECTION

    def __init__(self):
        self.address: InternetAddress = InternetAddress("0.0.0.0", 0, 4)
        self.systemAddresses: list[InternetAddress] = []
        self.sendPingTime: int = 0
        self.sendPongTime: int = 0

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putAddress(self.address)
        for address in self.systemAddresses:
            out.putAddress(address)
        out.putLong(self.sendPingTime)
        out.putLong(self.sendPongTime)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.address = in_.getAddress()

        # TODO: HACK!
        stopOffset = len(in_.getBuffer()) - 16  # buffer length - sizeof(sendPingTime) - sizeof(sendPongTime)
        dummy = InternetAddress("0.0.0.0", 0, 4)
        for i in range(RakLib.SYSTEM_ADDRESS_COUNT):
            if in_.getOffset() >= stopOffset:
                self.systemAddresses.append(InternetAddress(dummy.getIp(), dummy.getPort(), dummy.getVersion()))
            else:
                self.systemAddresses.append(in_.getAddress())

        self.sendPingTime = in_.getLong()
        self.sendPongTime = in_.getLong()