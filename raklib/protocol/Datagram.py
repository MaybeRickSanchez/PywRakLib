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

"""A RakNet datagram: a batch of encapsulated packets with a sequence number."""

from __future__ import annotations

from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.Packet import Packet
from raklib.protocol.PacketSerializer import PacketSerializer


class Datagram(Packet):
    BITFLAG_VALID = 0x80
    BITFLAG_ACK = 0x40
    BITFLAG_NAK = 0x20  # hasBAndAS for ACKs
    BITFLAG_PACKET_PAIR = 0x10
    BITFLAG_CONTINUOUS_SEND = 0x08
    BITFLAG_NEEDS_B_AND_AS = 0x04

    HEADER_SIZE = 1 + 3  # header flags (1) + sequence number (3)

    def __init__(self):
        self.headerFlags: int = 0
        self.packets: list[EncapsulatedPacket] = []
        self.seqNumber: int = 0

    def encodeHeader(self, out: PacketSerializer) -> None:
        out.putByte(self.BITFLAG_VALID | self.headerFlags)

    def encodePayload(self, out: PacketSerializer) -> None:
        out.putLTriad(self.seqNumber)
        for packet in self.packets:
            out.put(packet.toBinary())

    def length(self) -> int:
        length = self.HEADER_SIZE
        for packet in self.packets:
            length += packet.getTotalLength()
        return length

    def decodeHeader(self, in_: PacketSerializer) -> None:
        self.headerFlags = in_.getByte()

    def decodePayload(self, in_: PacketSerializer) -> None:
        self.seqNumber = in_.getLTriad()

        while not in_.feof():
            self.packets.append(EncapsulatedPacket.fromBinary(in_))

    # Alias so that callers expecting a PHP-style property access work.
    @property
    def sequenceNumber(self) -> int:
        return self.seqNumber

    @sequenceNumber.setter
    def sequenceNumber(self, value: int) -> None:
        self.seqNumber = value