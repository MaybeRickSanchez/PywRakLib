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

"""Base packet classes, ported from RakLib's ``Packet``, ``OfflineMessage`` and ``ConnectedPacket``."""

from __future__ import annotations

from raklib.protocol.PacketSerializer import PacketSerializer


class Packet:
    ID: int = -1

    def encode(self, out: PacketSerializer) -> None:
        self.encodeHeader(out)
        self.encodePayload(out)

    def encodeHeader(self, out: PacketSerializer) -> None:
        out.putByte(type(self).ID)

    def encodePayload(self, out: PacketSerializer) -> None:
        raise NotImplementedError

    def decode(self, in_: PacketSerializer) -> None:
        self.decodeHeader(in_)
        self.decodePayload(in_)

    def decodeHeader(self, in_: PacketSerializer) -> None:
        in_.getByte()  # PID

    def decodePayload(self, in_: PacketSerializer) -> None:
        raise NotImplementedError


class OfflineMessage(Packet):
    # Magic bytes used to distinguish offline messages from loose garbage.
    MAGIC = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"

    def __init__(self):
        self.magic: bytes = self.MAGIC

    def readMagic(self, in_: PacketSerializer) -> None:
        self.magic = in_.get(16)

    def writeMagic(self, out: PacketSerializer) -> None:
        out.put(self.magic)

    def isValid(self) -> bool:
        return self.magic == self.MAGIC


class ConnectedPacket(Packet):
    """Represents a packet which is sent inside an EncapsulatedPacket."""