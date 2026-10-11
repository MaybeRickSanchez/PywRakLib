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

"""An encapsulated packet, which is the RakNet unit carried inside a Datagram."""

from __future__ import annotations

from math import ceil

from raklib.protocol.PacketReliability import PacketReliability
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.protocol.SplitPacketInfo import SplitPacketInfo
from raklib.utils.binary import Binary, BinaryDataException


class EncapsulatedPacket:
    RELIABILITY_SHIFT = 5
    RELIABILITY_FLAGS = 0b111 << RELIABILITY_SHIFT

    SPLIT_FLAG = 0b00010000

    SPLIT_INFO_LENGTH = 4 + 2 + 4  # split count (4) + split ID (2) + split index (4)

    def __init__(self):
        self.reliability: int = 0
        self.messageIndex: int | None = None
        self.sequenceIndex: int | None = None
        self.orderIndex: int | None = None
        self.orderChannel: int | None = None
        self.splitInfo: SplitPacketInfo | None = None
        self.buffer: bytes = b""
        self.identifierACK: int | None = None

    @staticmethod
    def fromBinary(stream: PacketSerializer) -> "EncapsulatedPacket":
        packet = EncapsulatedPacket()

        flags = stream.getByte()
        reliability = (flags & EncapsulatedPacket.RELIABILITY_FLAGS) >> EncapsulatedPacket.RELIABILITY_SHIFT
        packet.reliability = reliability
        hasSplit = (flags & EncapsulatedPacket.SPLIT_FLAG) != 0

        length = int(ceil(stream.getShort() / 8))
        if length == 0:
            raise BinaryDataException("Encapsulated payload length cannot be zero")

        if PacketReliability.isReliable(reliability):
            packet.messageIndex = stream.getLTriad()

        if PacketReliability.isSequenced(reliability):
            packet.sequenceIndex = stream.getLTriad()

        if PacketReliability.isSequencedOrOrdered(reliability):
            packet.orderIndex = stream.getLTriad()
            packet.orderChannel = stream.getByte()

        if hasSplit:
            splitCount = stream.getInt()
            splitID = stream.getShort()
            splitIndex = stream.getInt()
            packet.splitInfo = SplitPacketInfo(splitID, splitIndex, splitCount)

        packet.buffer = stream.get(length)
        return packet

    def toBinary(self) -> bytes:
        result = bytearray()
        result.append(
            ((self.reliability << self.RELIABILITY_SHIFT) | (self.SPLIT_FLAG if self.splitInfo is not None else 0)) & 0xFF
        )
        result += Binary.writeShort(len(self.buffer) << 3)

        if PacketReliability.isReliable(self.reliability):
            if self.messageIndex is None:
                raise AssertionError(f"Message index must be set for reliability {self.reliability}")
            result += Binary.writeLTriad(self.messageIndex)

        if PacketReliability.isSequenced(self.reliability):
            if self.sequenceIndex is None:
                raise AssertionError(f"Sequence index must be set for reliability {self.reliability}")
            result += Binary.writeLTriad(self.sequenceIndex)

        if PacketReliability.isSequencedOrOrdered(self.reliability):
            if self.orderIndex is None:
                raise AssertionError(f"Order index must be set for reliability {self.reliability}")
            if self.orderChannel is None:
                raise AssertionError(f"Order channel must be set for reliability {self.reliability}")
            result += Binary.writeLTriad(self.orderIndex)
            result.append(self.orderChannel & 0xFF)

        if self.splitInfo is not None:
            result += Binary.writeInt(self.splitInfo.getTotalPartCount())
            result += Binary.writeShort(self.splitInfo.getId())
            result += Binary.writeInt(self.splitInfo.getPartIndex())

        result += self.buffer
        return bytes(result)

    def getHeaderLength(self) -> int:
        return (
            1  # reliability
            + 2  # length
            + (3 if PacketReliability.isReliable(self.reliability) else 0)  # message index
            + (3 if PacketReliability.isSequenced(self.reliability) else 0)  # sequence index
            + (3 + 1 if PacketReliability.isSequencedOrOrdered(self.reliability) else 0)  # order index + channel
            + (self.SPLIT_INFO_LENGTH if self.splitInfo is not None else 0)
        )

    def getTotalLength(self) -> int:
        return self.getHeaderLength() + len(self.buffer)

    def __str__(self) -> str:
        return repr(self.toBinary())