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

"""Base class for a RakNet session, shared by server and client implementations."""

from __future__ import annotations

import sys
import time

from raklib.generic.DisconnectReason import DisconnectReason
from raklib.generic.ReceiveReliabilityLayer import ReceiveReliabilityLayer
from raklib.generic.SendReliabilityLayer import SendReliabilityLayer
from raklib.protocol.ACK import ACK
from raklib.protocol.AcknowledgePacket import AcknowledgePacket
from raklib.protocol.ConnectedPacket import ConnectedPacket
from raklib.protocol.ConnectedPing import ConnectedPing
from raklib.protocol.ConnectedPong import ConnectedPong
from raklib.protocol.Datagram import Datagram
from raklib.protocol.DisconnectionNotification import DisconnectionNotification
from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.NACK import NACK
from raklib.protocol.Packet import Packet
from raklib.protocol.PacketReliability import PacketReliability
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import Logger, PrefixedLogger

_PHP_INT_MAX = sys.maxsize


class Session:
    STATE_CONNECTING = 0
    STATE_CONNECTED = 1
    STATE_DISCONNECT_PENDING = 2
    STATE_DISCONNECT_NOTIFIED = 3
    STATE_DISCONNECTED = 4

    MIN_MTU_SIZE = 400

    def __init__(
        self,
        logger: Logger,
        address: InternetAddress,
        clientId: int,
        mtuSize: int,
        recvMaxSplitParts: int = _PHP_INT_MAX,
        recvMaxConcurrentSplits: int = _PHP_INT_MAX,
    ):
        if mtuSize < self.MIN_MTU_SIZE:
            raise ValueError(f"MTU size must be at least {self.MIN_MTU_SIZE}, got {mtuSize}")

        self.logger = PrefixedLogger(logger, f"Session: {address.toString()}")
        self.address = address
        self._id = clientId

        self.state = self.STATE_CONNECTING

        self._lastUpdate = time.time()
        self._disconnectionTime = 0.0
        self._isActive = False
        self._lastPingTime = -1.0
        self._lastPingMeasure = 1

        self._recvLayer = ReceiveReliabilityLayer(
            self.logger,
            self._handleEncapsulatedPacketRouteCallback,
            self._sendAcknowledgePacket,
            recvMaxSplitParts,
            recvMaxConcurrentSplits,
        )
        self._sendLayer = SendReliabilityLayer(
            mtuSize,
            self._sendDatagramCallback,
            self._onPacketAck,
        )

    # ------------------------------------------------------------------ abstract API

    def sendPacket(self, packet: Packet) -> None:
        """Sends a packet in the appropriate way for the session type."""
        raise NotImplementedError

    def onPacketAck(self, identifierACK: int) -> None:
        """Called when a packet for which an ACK was requested is ACKed."""
        raise NotImplementedError

    def onDisconnect(self, reason: int) -> None:
        """Called when the session is terminated for any reason."""
        raise NotImplementedError

    def handleRakNetConnectionPacket(self, packet: bytes) -> None:
        """Called when a packet is received while the session is in the 'connecting' state."""
        raise NotImplementedError

    def onPacketReceive(self, packet: bytes) -> None:
        """Called when a user packet (ID >= ID_USER_PACKET_ENUM) is received from the remote peer."""
        raise NotImplementedError

    def onPingMeasure(self, pingMS: int) -> None:
        """Called when a new ping measurement is recorded."""
        raise NotImplementedError

    # ------------------------------------------------------------------ callbacks

    def _handleEncapsulatedPacketRouteCallback(self, packet: EncapsulatedPacket) -> None:
        self._handleEncapsulatedPacketRoute(packet)

    def _sendAcknowledgePacket(self, packet: AcknowledgePacket) -> None:
        self.sendPacket(packet)

    def _sendDatagramCallback(self, datagram: Datagram) -> None:
        self.sendPacket(datagram)

    def _onPacketAck(self, identifierACK: int) -> None:
        self.onPacketAck(identifierACK)

    # ------------------------------------------------------------------ accessors

    def getRakNetTimeMS(self) -> int:
        """
        Returns a monotonically increasing timestamp in milliseconds. It does not need to match UNIX time.
        This is used to calculate ping.
        """
        return time.perf_counter_ns() // 1_000_000

    def getLogger(self) -> Logger:
        return self.logger

    def getAddress(self) -> InternetAddress:
        return self.address

    def getID(self) -> int:
        return self._id

    def getState(self) -> int:
        return self.state

    def isTemporary(self) -> bool:
        return self.state == self.STATE_CONNECTING

    def isConnected(self) -> bool:
        return self.state not in (
            self.STATE_DISCONNECT_PENDING,
            self.STATE_DISCONNECT_NOTIFIED,
            self.STATE_DISCONNECTED,
        )

    # ------------------------------------------------------------------ lifecycle

    def update(self, time_: float) -> None:
        if not self._isActive and (self._lastUpdate + 10) < time_:
            self.forciblyDisconnect(DisconnectReason.PEER_TIMEOUT)
            return

        if self.state in (self.STATE_DISCONNECT_PENDING, self.STATE_DISCONNECT_NOTIFIED):
            if not self._sendLayer.needsUpdate() and not self._recvLayer.needsUpdate():
                if self.state == self.STATE_DISCONNECT_PENDING:
                    self.queueConnectedPacket(
                        DisconnectionNotification(), PacketReliability.RELIABLE_ORDERED, 0, True
                    )
                    self.state = self.STATE_DISCONNECT_NOTIFIED
                    self.logger.debug("All pending traffic flushed, sent disconnect notification")
                else:
                    self.state = self.STATE_DISCONNECTED
                    self.logger.debug("Client cleanly disconnected, marking session for destruction")
                    return
            elif self._disconnectionTime + 10 < time_:
                self.state = self.STATE_DISCONNECTED
                self.logger.debug("Timeout during graceful disconnect, forcibly closing session")
                return

        self._isActive = False

        self._recvLayer.update()
        self._sendLayer.update()

        if self._lastPingTime + 5 < time_:
            self.sendPing()
            self._lastPingTime = time_

    def queueConnectedPacket(
        self,
        packet: ConnectedPacket,
        reliability: int,
        orderChannel: int,
        immediate: bool = False,
    ) -> None:
        out = PacketSerializer()
        packet.encode(out)

        encapsulated = EncapsulatedPacket()
        encapsulated.reliability = reliability
        encapsulated.orderChannel = orderChannel
        encapsulated.buffer = out.getBuffer()

        self._sendLayer.addEncapsulatedToQueue(encapsulated, immediate)

    def addEncapsulatedToQueue(self, packet: EncapsulatedPacket, immediate: bool) -> None:
        self._sendLayer.addEncapsulatedToQueue(packet, immediate)

    def sendPing(self, reliability: int = PacketReliability.UNRELIABLE) -> None:
        self.queueConnectedPacket(ConnectedPing.create(self.getRakNetTimeMS()), reliability, 0, True)

    def _handleEncapsulatedPacketRoute(self, packet: EncapsulatedPacket) -> None:
        id_ = packet.buffer[0]
        if id_ < MessageIdentifiers.ID_USER_PACKET_ENUM:  # internal data packet
            if self.state == self.STATE_CONNECTING:
                self.handleRakNetConnectionPacket(packet.buffer)
            elif id_ == MessageIdentifiers.ID_DISCONNECTION_NOTIFICATION:
                self._handleRemoteDisconnect()
            elif id_ == MessageIdentifiers.ID_CONNECTED_PING:
                dataPacket = ConnectedPing()
                dataPacket.decode(PacketSerializer(packet.buffer))
                self.queueConnectedPacket(
                    ConnectedPong.create(dataPacket.sendPingTime, self.getRakNetTimeMS()),
                    PacketReliability.UNRELIABLE,
                    0,
                )
            elif id_ == MessageIdentifiers.ID_CONNECTED_PONG:
                dataPacket = ConnectedPong()
                dataPacket.decode(PacketSerializer(packet.buffer))
                self._handlePong(dataPacket.sendPingTime, dataPacket.sendPongTime)
        elif self.state == self.STATE_CONNECTED:
            self.onPacketReceive(packet.buffer)
        else:
            # $this->logger->notice("Received packet before connection: " . bin2hex($packet->buffer));
            pass

    def _handlePong(self, sendPingTime: int, sendPongTime: int) -> None:
        # TODO: clock differential stuff
        if sendPingTime < 0:
            self.logger.debug("Received invalid pong: timestamp overflow")
        else:
            currentTime = self.getRakNetTimeMS()
            if currentTime < sendPingTime:
                self.logger.debug(
                    f"Received invalid pong: timestamp is in the future by {sendPingTime - currentTime} ms"
                )
            else:
                self._lastPingMeasure = currentTime - sendPingTime
                self.onPingMeasure(self._lastPingMeasure)

    def handlePacket(self, packet: Packet) -> None:
        self._isActive = True
        self._lastUpdate = time.time()

        if isinstance(packet, Datagram):
            self._recvLayer.onDatagram(packet)
        elif isinstance(packet, ACK):
            self._sendLayer.onACK(packet)
        elif isinstance(packet, NACK):
            self._sendLayer.onNACK(packet)

    def initiateDisconnect(self, reason: int) -> None:
        """Initiates a graceful asynchronous disconnect which ensures both parties got all packets."""
        if self.isConnected():
            self.state = self.STATE_DISCONNECT_PENDING
            self._disconnectionTime = time.time()
            self.onDisconnect(reason)
            self.logger.debug(f'Requesting graceful disconnect because "{DisconnectReason.toString(reason)}"')

    def forciblyDisconnect(self, reason: int) -> None:
        """Disconnects the session with immediate effect, regardless of current session state."""
        self.state = self.STATE_DISCONNECTED
        self.onDisconnect(reason)
        self.logger.debug(f"Forcibly disconnecting session due to {DisconnectReason.toString(reason)}")

    def _handleRemoteDisconnect(self) -> None:
        # the client will expect an ACK for this; make sure it gets sent, because after forcible termination
        # there won't be any session ticks to update it
        self._recvLayer.update()

        if self.isConnected():
            # the client might have disconnected after the server sent a disconnect notification, but before the
            # client received it - in this case, we don't want to notify the event handler twice
            self.onDisconnect(DisconnectReason.CLIENT_DISCONNECT)
        self.state = self.STATE_DISCONNECTED
        self.logger.debug("Terminating session due to client disconnect")

    def isFullyDisconnected(self) -> bool:
        """Returns whether the session is ready to be destroyed."""
        return self.state == self.STATE_DISCONNECTED