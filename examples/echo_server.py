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
A minimal RakLib echo server.

It accepts RakNet connections, prints connection lifecycle events, and echoes back any user packets it receives
(inside the reliability layer). This demonstrates how to embed RakLib in an application: implement
``ServerEventListener`` and ``ServerEventSource`` and call :meth:`Server.tickProcessor` in a loop.

Usage: python examples/echo_server.py [bind-address] [port]
"""

from __future__ import annotations

import sys

from raklib.generic.DisconnectReason import DisconnectReason
from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.PacketReliability import PacketReliability
from raklib.server.Server import Server
from raklib.server.ServerEventListener import ServerEventListener
from raklib.server.ServerSocket import ServerSocket
from raklib.server.SimpleProtocolAcceptor import SimpleProtocolAcceptor
from raklib.utils.ExceptionTraceCleaner import ExceptionTraceCleaner
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import GlobalLogger


class EchoEventListener(ServerEventListener):
    def __init__(self):
        self.server: Server | None = None

    def onClientConnect(self, sessionId, address, port, clientID):
        self.server.getLogger().info(f"Client connected: session {sessionId} from {address}:{port}")

    def onClientDisconnect(self, sessionId, reason):
        self.server.getLogger().info(
            f"Client disconnected: session {sessionId} ({DisconnectReason.toString(reason)})"
        )

    def onPacketReceive(self, sessionId, packet):
        self.server.getLogger().info(f"Received {len(packet)} bytes from session {sessionId}")
        # Echo the payload back to the sender.
        response = EncapsulatedPacket()
        response.reliability = PacketReliability.RELIABLE_ORDERED
        response.orderChannel = 0
        response.buffer = packet
        self.server.sendEncapsulated(sessionId, response, True)

    def onRawPacketReceive(self, address, port, payload):
        self.server.getLogger().debug(f"Raw packet from {address}:{port}: {payload.hex()}")

    def onPacketAck(self, sessionId, identifierACK):
        pass

    def onBandwidthStatsUpdate(self, bytesSentDiff, bytesReceivedDiff):
        self.server.getLogger().debug(f"Sent {bytesSentDiff} bytes, received {bytesReceivedDiff} bytes")

    def onPingMeasure(self, sessionId, pingMS):
        self.server.getLogger().debug(f"Session {sessionId} ping: {pingMS}ms")


class EmptyEventSource:
    """No externally-driven events; the server only reacts to network traffic."""

    def process(self, server) -> bool:
        return False


def main(argv: list[str]) -> int:
    bindAddress = argv[1] if len(argv) > 1 else "0.0.0.0"
    port = int(argv[2]) if len(argv) > 2 else 19132

    logger = GlobalLogger.get()
    serverId = 0xDEADBEEF
    listener = EchoEventListener()

    server = Server(
        serverId=serverId,
        logger=logger,
        socket=ServerSocket(InternetAddress(bindAddress, port, 4)),
        maxMtuSize=1492,
        protocolAcceptor=SimpleProtocolAcceptor(6),
        eventSource=EmptyEventSource(),
        eventListener=listener,
        traceCleaner=ExceptionTraceCleaner(__file__),
    )
    listener.server = server
    server.setName("MCPE;RakLib Python Example;0;1.20.0;0;10;"
                   f"{serverId};RakLib Python;Survival;1;{port};{port};")

    logger.info(f"RakLib server listening on {bindAddress}:{port}")
    try:
        while True:
            server.tickProcessor()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.waitShutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))