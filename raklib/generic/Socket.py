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

"""Base UDP socket wrapper, ported from RakLib's ``Socket``."""

from __future__ import annotations

import socket

from raklib.generic.SocketException import SocketException


class Socket:
    def __init__(self, ipv6: bool):
        family = socket.AF_INET6 if ipv6 else socket.AF_INET
        try:
            self.socket = socket.socket(family, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        except OSError as e:
            raise SocketException(f"Failed to create socket: {e}") from e

        if ipv6:
            # Don't map IPv4 to IPv6; the implementation can create another RakLib instance to handle IPv4
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            except OSError:
                pass

    def getSocket(self) -> socket.socket:
        return self.socket

    def close(self) -> None:
        self.socket.close()

    def getLastError(self) -> int:
        return self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)

    def setSendBuffer(self, size: int) -> "Socket":
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)
        return self

    def setRecvBuffer(self, size: int) -> "Socket":
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
        return self

    def setRecvTimeout(self, seconds: int, microseconds: int = 0) -> "Socket":
        timeout = seconds + microseconds / 1_000_000
        self.socket.settimeout(timeout if timeout > 0 else None)
        return self

    def setBlocking(self, blocking: bool) -> None:
        self.socket.setblocking(blocking)