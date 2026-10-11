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

"""
Binary serialization helpers.

This is a port of pocketmine/binaryutils' ``Binary`` and ``BinaryStream`` classes, which RakLib depends on.

PHP integers are 64-bit signed natively, whereas Python integers are unbounded. To faithfully reproduce the
behaviour of the PHP implementation (e.g. the ``readLong()`` returning a negative value for values >= 2**63), the
read helpers deliberately wrap their results into the signed 64-bit range, and the write helpers mask their inputs
appropriately. JavaScript/Java/Go ports of RakNet may differ in this regard, but matching the reference
implementation exactly is the goal here.
"""

from __future__ import annotations

import struct
from typing import Final

INT64_MAX: Final = (1 << 63) - 1
INT64_MIN: Final = -(1 << 63)

_MASK64: Final = (1 << 64) - 1
_MASK32: Final = (1 << 32) - 1
_MASK16: Final = (1 << 16) - 1
_MASK8: Final = (1 << 8) - 1


class BinaryDataException(Exception):
    """Thrown when there are not enough bytes left in a buffer, or the data is invalid."""


def sign_byte(value: int) -> int:
    value &= _MASK8
    return value - 0x100 if value >= 0x80 else value


def unsign_byte(value: int) -> int:
    return value & _MASK8


def sign_short(value: int) -> int:
    value &= _MASK16
    return value - 0x10000 if value >= 0x8000 else value


def unsign_short(value: int) -> int:
    return value & _MASK16


def sign_int(value: int) -> int:
    value &= _MASK32
    return value - 0x100000000 if value >= 0x80000000 else value


def unsign_int(value: int) -> int:
    return value & _MASK32


def sign_long(value: int) -> int:
    value &= _MASK64
    return value - 0x10000000000000000 if value >= 0x8000000000000000 else value


def unsign_long(value: int) -> int:
    return value & _MASK64


class Binary:
    """Static methods for working with binary strings, mirroring PHP's ``Binary`` class."""

    SIZEOF_SHORT: Final = 2
    SIZEOF_INT: Final = 4
    SIZEOF_LONG: Final = 8

    SIZEOF_FLOAT: Final = 4
    SIZEOF_DOUBLE: Final = 8

    @staticmethod
    def signByte(value: int) -> int:
        return sign_byte(value)

    @staticmethod
    def unsignByte(value: int) -> int:
        return unsign_byte(value)

    @staticmethod
    def signShort(value: int) -> int:
        return sign_short(value)

    @staticmethod
    def unsignShort(value: int) -> int:
        return unsign_short(value)

    @staticmethod
    def signInt(value: int) -> int:
        return sign_int(value)

    @staticmethod
    def unsignInt(value: int) -> int:
        return unsign_int(value)

    @staticmethod
    def signLong(value: int) -> int:
        return sign_long(value)

    @staticmethod
    def unsignLong(value: int) -> int:
        return unsign_long(value)

    @staticmethod
    def flipShortEndianness(value: int) -> int:
        return Binary.readLShort(Binary.writeShort(value))

    @staticmethod
    def flipIntEndianness(value: int) -> int:
        return Binary.readLInt(Binary.writeInt(value))

    @staticmethod
    def flipLongEndianness(value: int) -> int:
        return Binary.readLLong(Binary.writeLong(value))

    @staticmethod
    def _safe_unpack(fmt: str, data: bytes, need_length: int) -> tuple:
        have_length = len(data)
        if have_length < need_length:
            raise BinaryDataException(f"Not enough bytes: need {need_length}, have {have_length}")
        return struct.unpack(fmt, data[:need_length])

    @staticmethod
    def readBool(b: bytes) -> bool:
        if len(b) < 1:
            raise BinaryDataException("Expected a string of length 1")
        return b[0] != 0

    @staticmethod
    def writeBool(b: bool) -> bytes:
        return b"\x01" if b else b"\x00"

    @staticmethod
    def readByte(c: bytes) -> int:
        if len(c) < 1:
            raise BinaryDataException("Expected a string of length 1")
        return c[0]

    @staticmethod
    def readSignedByte(c: bytes) -> int:
        return sign_byte(Binary.readByte(c))

    @staticmethod
    def writeByte(c: int) -> bytes:
        return bytes((c & _MASK8,))

    @staticmethod
    def readShort(data: bytes) -> int:
        return Binary._safe_unpack(">H", data, Binary.SIZEOF_SHORT)[0]

    @staticmethod
    def readSignedShort(data: bytes) -> int:
        return sign_short(Binary.readShort(data))

    @staticmethod
    def writeShort(value: int) -> bytes:
        return struct.pack(">H", value & _MASK16)

    @staticmethod
    def readLShort(data: bytes) -> int:
        return Binary._safe_unpack("<H", data, Binary.SIZEOF_SHORT)[0]

    @staticmethod
    def readSignedLShort(data: bytes) -> int:
        return sign_short(Binary.readLShort(data))

    @staticmethod
    def writeLShort(value: int) -> bytes:
        return struct.pack("<H", value & _MASK16)

    @staticmethod
    def readTriad(data: bytes) -> int:
        return Binary._safe_unpack(">I", b"\x00" + data[:3], Binary.SIZEOF_INT)[0]

    @staticmethod
    def writeTriad(value: int) -> bytes:
        return struct.pack(">I", value & _MASK32)[1:]

    @staticmethod
    def readLTriad(data: bytes) -> int:
        return Binary._safe_unpack("<I", data[:3] + b"\x00", Binary.SIZEOF_INT)[0]

    @staticmethod
    def writeLTriad(value: int) -> bytes:
        return struct.pack("<I", value & _MASK32)[:3]

    @staticmethod
    def readInt(data: bytes) -> int:
        return sign_int(Binary._safe_unpack(">I", data, Binary.SIZEOF_INT)[0])

    @staticmethod
    def writeInt(value: int) -> bytes:
        return struct.pack(">I", value & _MASK32)

    @staticmethod
    def readLInt(data: bytes) -> int:
        return sign_int(Binary._safe_unpack("<I", data, Binary.SIZEOF_INT)[0])

    @staticmethod
    def writeLInt(value: int) -> bytes:
        return struct.pack("<I", value & _MASK32)

    @staticmethod
    def readFloat(data: bytes) -> float:
        return Binary._safe_unpack(">f", data, Binary.SIZEOF_FLOAT)[0]

    @staticmethod
    def writeFloat(value: float) -> bytes:
        return struct.pack(">f", value)

    @staticmethod
    def readLFloat(data: bytes) -> float:
        return Binary._safe_unpack("<f", data, Binary.SIZEOF_FLOAT)[0]

    @staticmethod
    def writeLFloat(value: float) -> bytes:
        return struct.pack("<f", value)

    @staticmethod
    def readDouble(data: bytes) -> float:
        return Binary._safe_unpack(">d", data, Binary.SIZEOF_DOUBLE)[0]

    @staticmethod
    def writeDouble(value: float) -> bytes:
        return struct.pack(">d", value)

    @staticmethod
    def readLDouble(data: bytes) -> float:
        return Binary._safe_unpack("<d", data, Binary.SIZEOF_DOUBLE)[0]

    @staticmethod
    def writeLDouble(value: float) -> bytes:
        return struct.pack("<d", value)

    @staticmethod
    def readLong(data: bytes) -> int:
        return sign_long(Binary._safe_unpack(">Q", data, Binary.SIZEOF_LONG)[0])

    @staticmethod
    def writeLong(value: int) -> bytes:
        return struct.pack(">Q", value & _MASK64)

    @staticmethod
    def readLLong(data: bytes) -> int:
        return sign_long(Binary._safe_unpack("<Q", data, Binary.SIZEOF_LONG)[0])

    @staticmethod
    def writeLLong(value: int) -> bytes:
        return struct.pack("<Q", value & _MASK64)

    @staticmethod
    def readVarInt(buffer: bytes, offset: int = 0) -> tuple[int, int]:
        raw, offset = Binary.readUnsignedVarInt(buffer, offset)
        temp = ((raw >> 1) ^ (-(raw & 1))) & _MASK64
        result = temp ^ (raw & 0x8000000000000000)
        return sign_long(result), offset

    @staticmethod
    def readUnsignedVarInt(buffer: bytes, offset: int = 0) -> tuple[int, int]:
        value = 0
        i = 0
        while i <= 28:
            if offset >= len(buffer):
                raise BinaryDataException("No bytes left in buffer")
            b = buffer[offset]
            offset += 1
            value |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                return value & _MASK32, offset
            i += 7
        raise BinaryDataException("VarInt did not terminate after 5 bytes!")

    @staticmethod
    def writeVarInt(v: int) -> bytes:
        v = sign_int(v)
        return Binary.writeUnsignedVarInt((v << 1) ^ (v >> 31))

    @staticmethod
    def writeUnsignedVarInt(value: int) -> bytes:
        buf = bytearray()
        remaining = value & _MASK32
        for _ in range(5):
            bits = remaining & 0x7F
            if (remaining >> 7) != 0:
                buf.append(bits | 0x80)
            else:
                buf.append(bits & 0x7F)
                return bytes(buf)
            remaining = (remaining >> 7) & (INT64_MAX >> 6)
        raise ValueError("Value too large to be encoded as a VarInt")

    @staticmethod
    def readVarLong(buffer: bytes, offset: int = 0) -> tuple[int, int]:
        raw, offset = Binary.readUnsignedVarLong(buffer, offset)
        temp = ((raw >> 1) ^ (-(raw & 1))) & _MASK64
        result = temp ^ (raw & 0x8000000000000000)
        return sign_long(result), offset

    @staticmethod
    def readUnsignedVarLong(buffer: bytes, offset: int = 0) -> tuple[int, int]:
        value = 0
        i = 0
        while i <= 63:
            if offset >= len(buffer):
                raise BinaryDataException("No bytes left in buffer")
            b = buffer[offset]
            offset += 1
            value |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                return value & _MASK64, offset
            i += 7
        raise BinaryDataException("VarLong did not terminate after 10 bytes!")

    @staticmethod
    def writeVarLong(v: int) -> bytes:
        v = sign_long(v)
        return Binary.writeUnsignedVarLong((v << 1) ^ (v >> 63))

    @staticmethod
    def writeUnsignedVarLong(value: int) -> bytes:
        buf = bytearray()
        remaining = value & _MASK64
        for _ in range(10):
            bits = remaining & 0x7F
            if (remaining >> 7) != 0:
                buf.append(bits | 0x80)
            else:
                buf.append(bits & 0x7F)
                return bytes(buf)
            remaining = (remaining >> 7) & (INT64_MAX >> 6)
        raise ValueError("Value too large to be encoded as a VarLong")


class BinaryStream:
    """A stream for reading and writing binary data, mirroring PHP's ``BinaryStream`` class."""

    def __init__(self, buffer: bytes = b"", offset: int = 0):
        self.buffer: bytes = buffer
        self.offset: int = offset

    def rewind(self) -> None:
        self.offset = 0

    def setOffset(self, offset: int) -> None:
        self.offset = offset

    def getOffset(self) -> int:
        return self.offset

    def getBuffer(self) -> bytes:
        return self.buffer

    def get(self, length: int) -> bytes:
        if length == 0:
            return b""
        if length < 0:
            raise ValueError("Length must be positive")

        remaining = len(self.buffer) - self.offset
        if remaining < length:
            raise BinaryDataException(f"Not enough bytes left in buffer: need {length}, have {remaining}")

        result = self.buffer[self.offset:self.offset + length]
        self.offset += length
        return result

    def getRemaining(self) -> bytes:
        buflen = len(self.buffer)
        if self.offset >= buflen:
            raise BinaryDataException("No bytes left to read")
        result = self.buffer[self.offset:]
        self.offset = buflen
        return result

    def put(self, data: bytes) -> None:
        self.buffer += data

    def getBool(self) -> bool:
        return self.get(1) != b"\x00"

    def putBool(self, value: bool) -> None:
        self.buffer += b"\x01" if value else b"\x00"

    def getByte(self) -> int:
        return self.get(1)[0]

    def putByte(self, value: int) -> None:
        self.buffer += bytes((value & _MASK8,))

    def getShort(self) -> int:
        return Binary.readShort(self.get(2))

    def getSignedShort(self) -> int:
        return Binary.readSignedShort(self.get(2))

    def putShort(self, value: int) -> None:
        self.buffer += Binary.writeShort(value)

    def getLShort(self) -> int:
        return Binary.readLShort(self.get(2))

    def getSignedLShort(self) -> int:
        return Binary.readSignedLShort(self.get(2))

    def putLShort(self, value: int) -> None:
        self.buffer += Binary.writeLShort(value)

    def getTriad(self) -> int:
        return Binary.readTriad(self.get(3))

    def putTriad(self, value: int) -> None:
        self.buffer += Binary.writeTriad(value)

    def getLTriad(self) -> int:
        return Binary.readLTriad(self.get(3))

    def putLTriad(self, value: int) -> None:
        self.buffer += Binary.writeLTriad(value)

    def getInt(self) -> int:
        return Binary.readInt(self.get(4))

    def putInt(self, value: int) -> None:
        self.buffer += Binary.writeInt(value)

    def getLInt(self) -> int:
        return Binary.readLInt(self.get(4))

    def putLInt(self, value: int) -> None:
        self.buffer += Binary.writeLInt(value)

    def getFloat(self) -> float:
        return Binary.readFloat(self.get(4))

    def putFloat(self, value: float) -> None:
        self.buffer += Binary.writeFloat(value)

    def getLFloat(self) -> float:
        return Binary.readLFloat(self.get(4))

    def putLFloat(self, value: float) -> None:
        self.buffer += Binary.writeLFloat(value)

    def getDouble(self) -> float:
        return Binary.readDouble(self.get(8))

    def putDouble(self, value: float) -> None:
        self.buffer += Binary.writeDouble(value)

    def getLDouble(self) -> float:
        return Binary.readLDouble(self.get(8))

    def putLDouble(self, value: float) -> None:
        self.buffer += Binary.writeLDouble(value)

    def getLong(self) -> int:
        return Binary.readLong(self.get(8))

    def putLong(self, value: int) -> None:
        self.buffer += Binary.writeLong(value)

    def getLLong(self) -> int:
        return Binary.readLLong(self.get(8))

    def putLLong(self, value: int) -> None:
        self.buffer += Binary.writeLLong(value)

    def getUnsignedVarInt(self) -> int:
        value, self.offset = Binary.readUnsignedVarInt(self.buffer, self.offset)
        return value

    def putUnsignedVarInt(self, value: int) -> None:
        self.put(Binary.writeUnsignedVarInt(value))

    def getVarInt(self) -> int:
        value, self.offset = Binary.readVarInt(self.buffer, self.offset)
        return value

    def putVarInt(self, value: int) -> None:
        self.put(Binary.writeVarInt(value))

    def getUnsignedVarLong(self) -> int:
        value, self.offset = Binary.readUnsignedVarLong(self.buffer, self.offset)
        return value

    def putUnsignedVarLong(self, value: int) -> None:
        self.buffer += Binary.writeUnsignedVarLong(value)

    def getVarLong(self) -> int:
        value, self.offset = Binary.readVarLong(self.buffer, self.offset)
        return value

    def putVarLong(self, value: int) -> None:
        self.buffer += Binary.writeVarLong(value)

    def feof(self) -> bool:
        return self.offset >= len(self.buffer)