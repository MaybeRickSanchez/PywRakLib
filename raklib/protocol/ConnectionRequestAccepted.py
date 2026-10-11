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


class ConnectionRequestAccepted(ConnectedPacket):
    ID = MessageIdentifiers.ID_CONNECTION_REQUEST_ACCEPTED

    def __init__(self):
        self.address: InternetAddress = InternetAddress("0.0.0.0", 0, 4)
        self.systemAddresses: list[InternetAddress] = [InternetAddress("127.0.0.1", 0, 4)]
        self.sendPingTime: int = 0
        self.sendPongTime: int = 0

    @staticmethod
    def create(
        clientAddress: InternetAddress,
        systemAddresses: list[InternetAddress],
        sendPingTime: int,
        sendPongTime: int,
    ) -> "ConnectionRequestAccepted":
        result = ConnectionRequestAccepted()
        result.address = clientAddress
        result.systemAddresses = systemAddresses
        result.sendPingTime = sendPingTime
        result.sendPongTime = sendPongTime
        return result

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putAddress(self.address)
        out.putShort(0)

        dummy = InternetAddress("0.0.0.0", 0, 4)
        for i in range(RakLib.SYSTEM_ADDRESS_COUNT):
            out.putAddress(self.systemAddresses[i] if i < len(self.systemAddresses) else dummy)

        out.putLong(self.sendPingTime)
        out.putLong(self.sendPongTime)

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.address = in_.getAddress()
        in_.getShort()  # TODO: check this

        self.systemAddresses = []
        length = len(in_.getBuffer())
        dummy = InternetAddress("0.0.0.0", 0, 4)

        for i in range(RakLib.SYSTEM_ADDRESS_COUNT):
            # HACK: avoids trying to read too many addresses on bad data
            self.systemAddresses.append(in_.getAddress() if in_.getOffset() + 16 < length else dummy)

        self.sendPingTime = in_.getLong()
        self.sendPongTime = in_.getLong()