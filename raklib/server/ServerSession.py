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

"""Server-side RakNet session."""

from __future__ import annotations

from raklib.generic.Session import Session
from raklib.protocol.ConnectionRequest import ConnectionRequest
from raklib.protocol.ConnectionRequestAccepted import ConnectionRequestAccepted
from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.NewIncomingConnection import NewIncomingConnection
from raklib.protocol.Packet import Packet
from raklib.protocol.PacketReliability import PacketReliability
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import Logger


class ServerSession(Session):
    DEFAULT_MAX_SPLIT_PART_COUNT = 128
    DEFAULT_MAX_CONCURRENT_SPLIT_COUNT = 4

    def __init__(
        self,
        server,
        logger: Logger,
        address: InternetAddress,
        clientId: int,
        mtuSize: int,
        internalId: int,
        recvMaxSplitParts: int = DEFAULT_MAX_SPLIT_PART_COUNT,
        recvMaxConcurrentSplits: int = DEFAULT_MAX_CONCURRENT_SPLIT_COUNT,
    ):
        self._server = server
        self._internalId = internalId
        super().__init__(logger, address, clientId, mtuSize, recvMaxSplitParts, recvMaxConcurrentSplits)

    def getInternalId(self) -> int:
        """Returns an ID used to identify this session across threads."""
        return self._internalId

    def sendPacket(self, packet: Packet) -> None:
        self._server.sendPacket(packet, self.address)

    def onPacketAck(self, identifierACK: int) -> None:
        self._server.getEventListener().onPacketAck(self._internalId, identifierACK)

    def onDisconnect(self, reason: int) -> None:
        self._server.getEventListener().onClientDisconnect(self._internalId, reason)

    def handleRakNetConnectionPacket(self, packet: bytes) -> None:
        id_ = packet[0]
        if id_ == MessageIdentifiers.ID_CONNECTION_REQUEST:
            dataPacket = ConnectionRequest()
            dataPacket.decode(PacketSerializer(packet))
            self.queueConnectedPacket(
                ConnectionRequestAccepted.create(
                    self.address,
                    [],
                    dataPacket.sendPingTime,
                    self.getRakNetTimeMS(),
                ),
                PacketReliability.UNRELIABLE,
                0,
                True,
            )
        elif id_ == MessageIdentifiers.ID_NEW_INCOMING_CONNECTION:
            dataPacket = NewIncomingConnection()
            dataPacket.decode(PacketSerializer(packet))

            if dataPacket.address.getPort() == self._server.getPort() or not self._server.portChecking:
                self.state = self.STATE_CONNECTED  # FINALLY!
                self._server.openSession(self)

                # $this->handlePong(...) can't be used due to system-address count issues in MCPE >.<
                self.sendPing()

    def onPacketReceive(self, packet: bytes) -> None:
        self._server.getEventListener().onPacketReceive(self._internalId, packet)

    def onPingMeasure(self, pingMS: int) -> None:
        self._server.getEventListener().onPingMeasure(self._internalId, pingMS)