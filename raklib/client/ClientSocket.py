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

"""UDP client socket, ported from RakLib's ``ClientSocket``."""

from __future__ import annotations

import errno

from raklib.generic.Socket import Socket
from raklib.generic.SocketException import SocketException
from raklib.utils.InternetAddress import InternetAddress


class ClientSocket(Socket):
    def __init__(self, connectAddress: InternetAddress):
        self._connectAddress = connectAddress
        super().__init__(connectAddress.getVersion() == 6)

        try:
            self.socket.connect((connectAddress.getIp(), connectAddress.getPort()))
        except OSError as e:
            raise SocketException(
                f"Failed to connect to {connectAddress}: {e}", e.errno if e.errno is not None else 0
            ) from e

        # TODO: is an 8 MB buffer really appropriate for a client??
        self.setSendBuffer(1024 * 1024 * 8).setRecvBuffer(1024 * 1024 * 8)

    def getConnectAddress(self) -> InternetAddress:
        return self._connectAddress

    def readPacket(self) -> bytes | None:
        try:
            return self.socket.recv(65535)
        except BlockingIOError:
            return None
        except OSError as e:
            if e.errno == errno.EWOULDBLOCK:
                return None
            raise SocketException(f"Failed to recv (errno {e.errno}): {e}", e.errno) from e

    def writePacket(self, buffer: bytes) -> int:
        try:
            return self.socket.send(buffer)
        except OSError as e:
            raise SocketException(f"Failed to send packet (errno {e.errno}): {e}", e.errno) from e