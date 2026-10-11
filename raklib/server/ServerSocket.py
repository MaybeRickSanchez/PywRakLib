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

"""UDP server socket, ported from RakLib's ``ServerSocket``."""

from __future__ import annotations

import errno
import socket

from raklib.generic.Socket import Socket
from raklib.generic.SocketException import SocketException
from raklib.utils.InternetAddress import InternetAddress


class ServerSocket(Socket):
    def __init__(self, bindAddress: InternetAddress):
        self._bindAddress = bindAddress
        super().__init__(bindAddress.getVersion() == 6)

        try:
            self.socket.bind((bindAddress.getIp(), bindAddress.getPort()))
        except OSError as e:
            error = e.errno
            if error == errno.EADDRINUSE:  # platform error messages aren't consistent
                raise SocketException(
                    f"Failed to bind socket: Something else is already running on {bindAddress}",
                    error if error is not None else 0,
                ) from e
            raise SocketException(
                f"Failed to bind to {bindAddress}: {e}", error if error is not None else 0
            ) from e

        self.setSendBuffer(1024 * 1024 * 8).setRecvBuffer(1024 * 1024 * 8)

    def getBindAddress(self) -> InternetAddress:
        return self._bindAddress

    def enableBroadcast(self) -> None:
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def disableBroadcast(self) -> None:
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 0)

    def readPacket(self):
        """
        Reads a packet from the socket.

        :return: a tuple ``(buffer, source, port)``, where buffer is ``None`` if no data is available.
        :raises SocketException: on a real socket error (e.g. ECONNRESET)
        """
        try:
            buffer, source = self.socket.recvfrom(65535)
        except BlockingIOError:
            return None, None, None
        except TimeoutError:
            raise
        except OSError as e:
            if e.errno == errno.EWOULDBLOCK:
                return None, None, None
            raise SocketException(f"Failed to recv (errno {e.errno}): {e}", e.errno) from e

        return buffer, source[0], source[1]

    def writePacket(self, buffer: bytes, dest: str, port: int) -> int:
        try:
            return self.socket.sendto(buffer, (dest, port))
        except OSError as e:
            raise SocketException(f"Failed to send to {dest} {port} (errno {e.errno}): {e}", e.errno) from e