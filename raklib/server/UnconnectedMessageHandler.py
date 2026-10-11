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

"""Handles unconnected (offline) RakNet messages, including the connection handshake."""

from __future__ import annotations

import random
import zlib

from raklib.generic.Session import Session
from raklib.protocol.IncompatibleProtocolVersion import IncompatibleProtocolVersion
from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.OpenConnectionReply1 import OpenConnectionReply1
from raklib.protocol.OpenConnectionReply2 import OpenConnectionReply2
from raklib.protocol.OpenConnectionRequest1 import OpenConnectionRequest1
from raklib.protocol.OpenConnectionRequest2 import OpenConnectionRequest2
from raklib.protocol.Packet import OfflineMessage
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.protocol.UnconnectedPing import UnconnectedPing
from raklib.protocol.UnconnectedPingOpenConnections import UnconnectedPingOpenConnections
from raklib.protocol.UnconnectedPong import UnconnectedPong
from raklib.utils.binary import Binary
from raklib.utils.InternetAddress import InternetAddress


class UnconnectedMessageHandler:
    def __init__(self, server, protocolAcceptor, antiIpSpoofCookies: bool = True):
        self._server = server
        self._protocolAcceptor = protocolAcceptor
        self._antiIpSpoofCookies = antiIpSpoofCookies

        self._packetPool: list[type[OfflineMessage] | None] = [None] * 256
        self._registerPackets()

        self._currentCookieSalt: bytes = self._newCookieSalt()
        self._previousCookieSalt: bytes = self._currentCookieSalt
        self._cookieMismatches = 0

    @staticmethod
    def _newCookieSalt() -> bytes:
        return Binary.writeLong(random.randint(-(2 ** 63), 2 ** 63 - 1))

    def rotateCookieSalts(self) -> None:
        self._previousCookieSalt = self._currentCookieSalt
        self._currentCookieSalt = self._newCookieSalt()
        self._cookieMismatches = 0

    @staticmethod
    def _calculateCookieWithSalt(address: InternetAddress, salt: bytes) -> int:
        preimage = (
            str(len(address.getIp())).encode()
            + address.getIp().encode()
            + Binary.writeShort(address.getPort())
            + salt
        )
        return zlib.crc32(preimage) & 0xFFFFFFFF

    def _calculateCookie(self, address: InternetAddress) -> int:
        return self._calculateCookieWithSalt(address, self._currentCookieSalt)

    def getCookieMismatchSinceLastRotation(self) -> int:
        return self._cookieMismatches

    def handleRaw(self, payload: bytes, address: InternetAddress) -> bool:
        if payload == b"":
            return False
        pk = self._getPacketFromPool(payload)
        if pk is None:
            return False
        reader = PacketSerializer(payload)
        pk.decode(reader)
        if not pk.isValid():
            return False
        if not reader.feof():
            remains = reader.getBuffer()[reader.getOffset():]
            self._server.getLogger().debug(
                f"Still {len(remains)} bytes unread in {type(pk).__name__} from {address}"
            )
        return self._handle(pk, address)

    def _handle(self, packet: OfflineMessage, address: InternetAddress) -> bool:
        if isinstance(packet, UnconnectedPing):
            self._server.sendPacket(
                UnconnectedPong.create(packet.sendPingTime, self._server.getID(), self._server.getName()),
                address,
            )
        elif isinstance(packet, OpenConnectionRequest1):
            if not self._protocolAcceptor.accepts(packet.protocol):
                self._server.sendPacket(
                    IncompatibleProtocolVersion.create(
                        self._protocolAcceptor.getPrimaryVersion(), self._server.getID()
                    ),
                    address,
                )
                self._server.getLogger().notice(
                    f"Refused connection from {address} due to incompatible RakNet protocol version "
                    f"(version {packet.protocol})"
                )
            else:
                # IP header size (20 bytes) + UDP header size (8 bytes)
                self._server.sendPacket(
                    OpenConnectionReply1.create(
                        self._server.getID(),
                        self._calculateCookie(address) if self._antiIpSpoofCookies else None,
                        packet.mtuSize + 28,
                    ),
                    address,
                )
        elif isinstance(packet, OpenConnectionRequest2):
            if self._antiIpSpoofCookies:
                cookie1 = self._calculateCookie(address)
                cookie2 = self._calculateCookieWithSalt(address, self._previousCookieSalt)
                if packet.cookie != cookie1 and packet.cookie != cookie2:
                    self._cookieMismatches += 1
                    # don't log this by default; we also don't block the IP since this is probably spoofed
                    return True
                else:
                    self._server.getLogger().debug(
                        f"Cookie check succeeded for {address} with cookie {packet.cookie} "
                        f"(cookie1: {cookie1}, cookie2: {cookie2})"
                    )
            else:
                self._server.getLogger().debug(f"No cookie check performed for {address}")

            if packet.serverAddress.getPort() == self._server.getPort() or not self._server.portChecking:
                if packet.mtuSize < Session.MIN_MTU_SIZE:
                    self._server.getLogger().debug(
                        f"Not creating session for {address} due to bad MTU size {packet.mtuSize}"
                    )
                    return True
                existingSession = self._server.getSessionByAddress(address)
                if existingSession is not None and existingSession.isConnected():
                    # for redundancy, in case someone rips up Server - we really don't want connected sessions
                    # getting overwritten
                    self._server.getLogger().debug(
                        f"Not creating session for {address} due to session already opened"
                    )
                    return True
                # Max size, do not allow creating large buffers to fill server memory
                mtuSize = min(packet.mtuSize, self._server.getMaxMtuSize())
                self._server.sendPacket(
                    OpenConnectionReply2.create(self._server.getID(), address, mtuSize, False), address
                )
                self._server.createSession(address, packet.clientID, mtuSize)
            else:
                self._server.getLogger().debug(
                    f"Not creating session for {address} due to mismatched port, "
                    f"expected {self._server.getPort()}, got {packet.serverAddress.getPort()}"
                )
        else:
            return False

        return True

    def _registerPacket(self, id_: int, cls: type[OfflineMessage]) -> None:
        self._packetPool[id_] = cls

    def _getPacketFromPool(self, buffer: bytes) -> OfflineMessage | None:
        cls = self._packetPool[buffer[0]]
        if cls is not None:
            return cls()
        return None

    def _registerPackets(self) -> None:
        self._registerPacket(MessageIdentifiers.ID_UNCONNECTED_PING, UnconnectedPing)
        self._registerPacket(
            MessageIdentifiers.ID_UNCONNECTED_PING_OPEN_CONNECTIONS, UnconnectedPingOpenConnections
        )
        self._registerPacket(MessageIdentifiers.ID_OPEN_CONNECTION_REQUEST_1, OpenConnectionRequest1)
        self._registerPacket(MessageIdentifiers.ID_OPEN_CONNECTION_REQUEST_2, OpenConnectionRequest2)