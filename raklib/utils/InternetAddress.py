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

"""A simple IP address + port pair."""

from __future__ import annotations


class InternetAddress:
    __slots__ = ("_ip", "_port", "_version")

    def __init__(self, ip: str, port: int, version: int):
        if port < 0 or port > 65535:
            raise ValueError("Invalid port range")

        self._ip = ip
        self._port = port
        self._version = version

    def getIp(self) -> str:
        return self._ip

    def getPort(self) -> int:
        return self._port

    def getVersion(self) -> int:
        return self._version

    def __str__(self) -> str:
        return self._ip + " " + str(self._port)

    def toString(self) -> str:
        return str(self)

    def equals(self, address: "InternetAddress") -> bool:
        return (
            self._ip == address._ip
            and self._port == address._port
            and self._version == address._version
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, InternetAddress):
            return self.equals(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._ip, self._port, self._version))

    def __repr__(self) -> str:
        return f"InternetAddress({self._ip!r}, {self._port}, {self._version})"