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
A UDP proxy for RakNet, ported from RakLib's ``tools/proxy.php``.

It caches ping responses from the backend server and relays all other traffic, which is useful for making a
PocketMine-MP server reachable through the machine running this proxy.
"""

from __future__ import annotations

import select
import socket
import sys
import time

from raklib.client.ClientSocket import ClientSocket
from raklib.generic.SocketException import SocketException
from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.server.ServerSocket import ServerSocket
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import GlobalLogger

INT32_MAX = 2 ** 31 - 1


class ClientSession:
    def __init__(self, address: InternetAddress, proxyToServerSocket: ClientSocket):
        self._address = address
        self._proxyToServerSocket = proxyToServerSocket
        self._lastUsedTime = int(time.time())

    def getAddress(self) -> InternetAddress:
        return self._address

    def getSocket(self) -> ClientSocket:
        return self._proxyToServerSocket

    def setActive(self) -> None:
        self._lastUsedTime = int(time.time())

    def isActive(self) -> bool:
        return int(time.time()) - self._lastUsedTime < 10


def serverToClientRelay(client: ClientSession, clientProxySocket: ServerSocket) -> None:
    buffer = client.getSocket().readPacket()
    if buffer is not None:
        clientProxySocket.writePacket(buffer, client.getAddress().getIp(), client.getAddress().getPort())


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    logger = GlobalLogger.get()
    bindAddr = "0.0.0.0"
    bindPort = 19132

    if len(argv) == 3:
        serverAddress = argv[1]
        serverPort = int(argv[2])
    elif len(argv) == 1:
        serverAddress = input("Enter server address: ").strip()
        serverPort = int(input("Enter server port: ").strip())
    else:
        print("Usage: python proxy.py [bind address] [bind port]")
        return 1

    try:
        serverAddress = socket.gethostbyname(serverAddress)
    except OSError:
        pass

    if serverPort != 19132:
        logger.warning(
            "You may experience problems connecting to PocketMine-MP servers on ports other than 19132 "
            "if the server has port checking enabled"
        )

    logger.info("Opening listen socket")
    try:
        proxyToServerUnconnectedSocket = ClientSocket(InternetAddress(serverAddress, serverPort, 4))
        proxyToServerUnconnectedSocket.setBlocking(False)
    except SocketException as e:
        logger.emergency(f"Can't connect to {serverAddress} on port {serverPort}, is the server online?")
        logger.emergency(str(e))
        return 1

    proxyAddr, proxyPort = proxyToServerUnconnectedSocket.getSocket().getsockname()[:2]
    logger.info(
        f"Listening on {bindAddr}:{bindPort}, sending from {proxyAddr}:{proxyPort}, "
        f"sending to {serverAddress}:{serverPort}"
    )

    try:
        clientProxySocket = ServerSocket(InternetAddress(bindAddr, bindPort, 4))
        clientProxySocket.setBlocking(False)
    except SocketException as e:
        logger.emergency(f"Can't bind to {bindAddr} on port {bindPort}, is something already using that port?")
        logger.emergency(str(e))
        return 1

    logger.info("Press CTRL+C to stop the proxy")

    # ip => port => ClientSession
    clients: dict[str, dict[int, ClientSession]] = {}
    mostRecentPong: bytes | None = None

    try:
        while True:
            readSockets = [clientProxySocket.getSocket(), proxyToServerUnconnectedSocket.getSocket()]
            clientIndex: dict[socket.socket, ClientSession] = {}
            for ipClients in clients.values():
                for client in ipClients.values():
                    sock = client.getSocket().getSocket()
                    readSockets.append(sock)
                    clientIndex[sock] = client

            readable, _, _ = select.select(readSockets, [], [], 10)
            for sock in readable:
                if sock in clientIndex:
                    serverToClientRelay(clientIndex[sock], clientProxySocket)
                elif sock is proxyToServerUnconnectedSocket.getSocket():
                    buffer = proxyToServerUnconnectedSocket.readPacket()
                    if buffer and buffer[0] == MessageIdentifiers.ID_UNCONNECTED_PONG:
                        mostRecentPong = buffer
                        logger.info(
                            "Caching ping response from server: "
                            + "".join(c if 32 <= ord(c) < 127 else "." for c in buffer.decode("latin-1"))
                        )
                elif sock is clientProxySocket.getSocket():
                    try:
                        result = clientProxySocket.readPacket()
                    except SocketException as e:
                        if e.code == 104:  # ECONNRESET
                            continue
                        logger.error(f"Socket error: {e}")
                        continue

                    buffer, recvAddr, recvPort = result
                    if not buffer:
                        continue

                    if recvAddr in clients and recvPort in clients[recvAddr]:
                        client = clients[recvAddr][recvPort]
                        client.setActive()
                        client.getSocket().writePacket(buffer)
                    elif buffer[0] == MessageIdentifiers.ID_UNCONNECTED_PING:
                        logger.info(f"Got ping from {recvAddr} on port {recvPort}, pinging server")
                        proxyToServerUnconnectedSocket.writePacket(buffer)

                        if mostRecentPong is not None:
                            clientProxySocket.writePacket(mostRecentPong, recvAddr, recvPort)
                        else:
                            logger.info("No cached ping response, waiting for server to respond")
                    elif buffer[0] == MessageIdentifiers.ID_OPEN_CONNECTION_REQUEST_1:
                        logger.info(f"Got connection from {recvAddr} on port {recvPort}")
                        proxyToServerUnconnectedSocket.writePacket(buffer)
                        client = ClientSession(
                            InternetAddress(recvAddr, recvPort, 4),
                            ClientSocket(InternetAddress(serverAddress, serverPort, 4)),
                        )
                        client.getSocket().setBlocking(False)
                        clients.setdefault(recvAddr, {})[recvPort] = client
                        thisProxyAddr, thisProxyPort = client.getSocket().getSocket().getsockname()[:2]
                        logger.info(
                            f"Established connection: {recvAddr}:{recvPort} <-> "
                            f"{thisProxyAddr}:{thisProxyPort} <-> {serverAddress}:{serverPort}"
                        )
                    else:
                        logger.warning(
                            f"Unexpected packet from unconnected client {recvAddr} on port {recvPort}: "
                            f"0x{buffer.hex()}"
                        )
                else:
                    raise RuntimeError("Unexpected socket in select result")

            for ip in list(clients.keys()):
                for port in list(clients[ip].keys()):
                    if not clients[ip][port].isActive():
                        logger.info(f"Closing session for client {ip}:{port}")
                        del clients[ip][port]
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))