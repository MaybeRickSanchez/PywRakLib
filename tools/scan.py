#!/usr/bin/env python3
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
Broadcasts RakNet unconnected pings and prints pongs, ported from RakLib's ``tools/scan.php``.

Usage: python scan.py <broadcast address> <port>
"""

from __future__ import annotations

import os
import socket
import sys
import time

from raklib.generic.SocketException import SocketException
from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.protocol.UnconnectedPing import UnconnectedPing
from raklib.server.ServerSocket import ServerSocket
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import GlobalLogger

INT32_MAX = 2 ** 31 - 1


def sendPing(sock: ServerSocket, broadcastAddress: str, port: int, clientId: int) -> None:
    ping = UnconnectedPing()
    ping.clientId = clientId
    ping.sendPingTime = time.perf_counter_ns() // 1_000_000

    serializer = PacketSerializer()
    ping.encode(serializer)
    sock.writePacket(serializer.getBuffer(), broadcastAddress, port)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    logger = GlobalLogger.get()
    if len(argv) == 3:
        broadcastAddress = argv[1]
        port = int(argv[2])
    else:
        print("Usage: python scan.py <broadcast address> <port>")
        return 1

    if "." in broadcastAddress:
        bindAddress = InternetAddress("0.0.0.0", 0, 4)
    else:
        bindAddress = InternetAddress("::", 0, 6)

    sock = ServerSocket(bindAddress)
    sock.enableBroadcast()
    clientId = int.from_bytes(os.urandom(4), "big") % (INT32_MAX + 1)
    logger.info(f"Listening on {bindAddress}")
    logger.info("Press CTRL+C to stop")

    sendPing(sock, broadcastAddress, port, clientId)

    sock.getSocket().settimeout(1)
    try:
        while True:
            try:
                pong, serverIp, serverPort = sock.readPacket()
                if pong is not None and pong[0] == MessageIdentifiers.ID_UNCONNECTED_PONG:
                    logger.info(f"Pong received from {serverIp}:{serverPort}: {pong}")
            except (SocketException, socket.timeout, TimeoutError):
                sendPing(sock, broadcastAddress, port, clientId)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))