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

"""Serializer with RakLib-specific extensions on top of :class:`~raklib.utils.binary.BinaryStream`."""

from __future__ import annotations

import ipaddress

from raklib.utils.binary import BinaryDataException, BinaryStream
from raklib.utils.InternetAddress import InternetAddress


class PacketSerializer(BinaryStream):
    IPV4_SIZE = 1 + 4 + 2  # type (1) + ip (4) + port (2)
    IPV6_SIZE = 1 + 2 + 2 + 4 + 16 + 4  # type + family + port + flow info + ip + scope id

    def getString(self) -> bytes:
        return self.get(self.getShort())

    def getAddress(self) -> InternetAddress:
        version = self.getByte()
        if version == 4:
            addr = (
                f"{(~self.getByte()) & 0xFF}."
                f"{(~self.getByte()) & 0xFF}."
                f"{(~self.getByte()) & 0xFF}."
                f"{(~self.getByte()) & 0xFF}"
            )
            port = self.getShort()
            return InternetAddress(addr, port, version)
        elif version == 6:
            # http://man7.org/linux/man-pages/man7/ipv6.7.html
            self.getLShort()  # Family, AF_INET6
            port = self.getShort()
            self.getInt()  # flow info
            raw = self.get(16)
            try:
                addr = str(ipaddress.IPv6Address(raw))
            except ipaddress.AddressValueError as e:
                raise BinaryDataException("Failed to parse IPv6 address") from e
            self.getInt()  # scope ID
            return InternetAddress(addr, port, version)
        else:
            raise BinaryDataException(f"Unknown IP address version {version}")

    def putString(self, value: bytes | str) -> None:
        if isinstance(value, str):
            value = value.encode("utf-8")
        self.putShort(len(value))
        self.put(value)

    def putAddress(self, address: InternetAddress) -> None:
        version = address.getVersion()
        self.putByte(version)
        if version == 4:
            parts = address.getIp().split(".")
            if len(parts) != 4:
                raise AssertionError(
                    f"Wrong number of parts in IPv4 IP, expected 4, got {len(parts)}"
                )
            for b in parts:
                self.putByte((~(int(b))) & 0xFF)
            self.putShort(address.getPort())
        elif version == 6:
            self.putLShort(10)  # AF_INET6
            self.putShort(address.getPort())
            self.putInt(0)
            try:
                raw = ipaddress.IPv6Address(address.getIp()).packed
            except ipaddress.AddressValueError as e:
                raise ValueError("Invalid IPv6 address could not be encoded") from e
            self.put(raw)
            self.putInt(0)
        else:
            raise ValueError(f"IP version {version} is not supported")