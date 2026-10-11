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

import unittest

from raklib.utils.binary import Binary, BinaryDataException, BinaryStream


class BinaryTest(unittest.TestCase):
    def test_int64_signed_roundtrip(self):
        self.assertEqual(-1, Binary.readLLong(b"\xff" * 8))
        self.assertEqual(b"\xff" * 8, Binary.writeLLong(-1))
        self.assertEqual(-1, Binary.readLong(b"\xff" * 8))
        self.assertEqual(b"\xff" * 8, Binary.writeLong(-1))

    def test_unsigned_wrappers(self):
        # readInt/readLInt return signed values (matching PHP); unsignInt recovers the unsigned form.
        self.assertEqual(-1, Binary.readInt(b"\xff\xff\xff\xff"))
        self.assertEqual(0xFFFFFFFF, Binary.unsignInt(Binary.readInt(b"\xff\xff\xff\xff")))
        self.assertEqual(-1, Binary.readLInt(b"\xff\xff\xff\xff"))
        self.assertEqual(0xFFFFFFFF, Binary.unsignInt(Binary.readLInt(b"\xff\xff\xff\xff")))

    def test_triad(self):
        self.assertEqual(b"\x56\x34\x12", Binary.writeLTriad(0x123456))
        self.assertEqual(0x123456, Binary.readLTriad(b"\x56\x34\x12"))
        self.assertEqual(b"\x12\x34\x56", Binary.writeTriad(0x123456))
        self.assertEqual(0x123456, Binary.readTriad(b"\x12\x34\x56"))

    def test_big_endian(self):
        self.assertEqual(b"\x00\x01", Binary.writeShort(1))
        self.assertEqual(1, Binary.readShort(b"\x00\x01"))
        self.assertEqual(b"\x00\x00\x00\x2a", Binary.writeInt(42))

    def test_varints(self):
        for value in (0, 1, 127, 128, 300, 2 ** 31 - 1):
            self.assertEqual(value, Binary.readUnsignedVarInt(Binary.writeUnsignedVarInt(value))[0])
        for value in (0, -1, 1, -300, 2 ** 31 - 1, -(2 ** 31)):
            self.assertEqual(value, Binary.readVarInt(Binary.writeVarInt(value))[0])

    def test_stream_not_enough_bytes(self):
        s = BinaryStream(b"\x01")
        with self.assertRaises(BinaryDataException):
            s.get(4)

    def test_stream_feof(self):
        s = BinaryStream(b"\x01\x02")
        s.get(2)
        self.assertTrue(s.feof())


if __name__ == "__main__":
    unittest.main()