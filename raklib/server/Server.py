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

"""The main RakLib server, ported from RakLib's ``Server``."""

from __future__ import annotations

import errno
import re
import time

from raklib.generic.DisconnectReason import DisconnectReason
from raklib.generic.PacketHandlingException import PacketHandlingException
from raklib.generic.Session import Session
from raklib.generic.SocketException import SocketException
from raklib.protocol.ACK import ACK
from raklib.protocol.Datagram import Datagram
from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.NACK import NACK
from raklib.protocol.Packet import Packet
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.server.ServerInterface import ServerInterface
from raklib.server.ServerSession import ServerSession
from raklib.server.ServerSocket import ServerSocket
from raklib.server.UnconnectedMessageHandler import UnconnectedMessageHandler
from raklib.utils.binary import BinaryDataException
from raklib.utils.ExceptionTraceCleaner import ExceptionTraceCleaner
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import BufferedLogger, Logger

_PHP_INT_MAX = 2 ** 63 - 1


class Server(ServerInterface):
    RAKLIB_TPS = 100
    RAKLIB_TIME_PER_TICK = 1 / RAKLIB_TPS
    BLOCK_MESSAGE_SUPPRESSION_THRESHOLD = 2
    PACKET_ERROR_SUPPRESSION_THRESHOLD = 2

    def __init__(
        self,
        serverId: int,
        logger: Logger,
        socket: ServerSocket,
        maxMtuSize: int,
        protocolAcceptor,
        eventSource,
        eventListener,
        traceCleaner: ExceptionTraceCleaner,
        recvMaxSplitParts: int = ServerSession.DEFAULT_MAX_SPLIT_PART_COUNT,
        recvMaxConcurrentSplits: int = ServerSession.DEFAULT_MAX_CONCURRENT_SPLIT_COUNT,
        blockMessageSuppressionThreshold: int = BLOCK_MESSAGE_SUPPRESSION_THRESHOLD,
        packetErrorSuppressionThreshold: int = PACKET_ERROR_SUPPRESSION_THRESHOLD,
        blockIpOnPacketErrors: bool = True,
        cookieRotationIntervalSeconds: int = 5,
    ):
        if maxMtuSize < Session.MIN_MTU_SIZE:
            raise ValueError(f"MTU size must be at least {Session.MIN_MTU_SIZE}, got {maxMtuSize}")

        self._serverId = serverId
        self._logger = logger
        self._socket = socket
        self._maxMtuSize = maxMtuSize
        self._eventSource = eventSource
        self._eventListener = eventListener
        self._traceCleaner = traceCleaner
        self._recvMaxSplitParts = recvMaxSplitParts
        self._recvMaxConcurrentSplits = recvMaxConcurrentSplits
        self._blockMessageSuppressionThreshold = blockMessageSuppressionThreshold
        self._packetErrorSuppressionThreshold = packetErrorSuppressionThreshold
        self._blockIpOnPacketErrors = blockIpOnPacketErrors

        self._socket.setBlocking(False)

        self._cookieRotationIntervalTicks = cookieRotationIntervalSeconds * self.RAKLIB_TPS
        self._unconnectedMessageHandler = UnconnectedMessageHandler(
            self, protocolAcceptor, cookieRotationIntervalSeconds > 0
        )

        self.receiveBytes = 0
        self.sendBytes = 0

        self._sessionsByAddress: dict[str, ServerSession] = {}
        self._sessions: dict[int, ServerSession] = {}

        self._name: str = ""
        self._packetLimit = 200
        self._shutdown = False
        self._ticks = 0

        self._block: dict[str, int] = {}
        self._ipSec: dict[str, int] = {}
        self._blockedSinceLastUpdate = 0
        self._packetErrorsSinceLastUpdate = 0

        self._rawPacketFilters: list[str] = []
        self._rawPacketRegexes: list[re.Pattern[bytes]] = []

        self.portChecking = False

        self._nextSessionId = 0

    def getPort(self) -> int:
        return self._socket.getBindAddress().getPort()

    def getMaxMtuSize(self) -> int:
        return self._maxMtuSize

    def getLogger(self) -> Logger:
        return self._logger

    def tickProcessor(self) -> None:
        start = time.time()

        # The below code is designed to allow co-op between sending and receiving to avoid slowing down either one
        # when high traffic is coming either way. Yielding will occur after 100 messages.
        stream = True
        socket = True
        while stream or socket:
            stream = not self._shutdown
            i = 0
            while i < 100 and stream and not self._shutdown:
                stream = self._eventSource.process(self)
                i += 1

            socket = True
            i = 0
            while i < 100 and socket:
                socket = self._receivePacket()
                i += 1

        self._tick()

        elapsed = time.time() - start
        if elapsed < self.RAKLIB_TIME_PER_TICK:
            time.sleep(self.RAKLIB_TIME_PER_TICK - elapsed)

    def waitShutdown(self) -> None:
        """Disconnects all sessions and blocks until everything has been shut down properly."""
        self._shutdown = True

        while self._eventSource.process(self):
            # Ensure that any late messages are processed before we start initiating server disconnects
            pass

        for session in list(self._sessions.values()):
            session.initiateDisconnect(DisconnectReason.SERVER_SHUTDOWN)

        while len(self._sessions) > 0:
            self.tickProcessor()

        self._socket.close()
        self._logger.debug("Graceful shutdown complete")

    def _tick(self) -> None:
        time_ = time.time()
        for session in list(self._sessions.values()):
            session.update(time_)
            if session.isFullyDisconnected():
                self._removeSessionInternal(session)

        self._ipSec = {}

        if not self._shutdown and (self._ticks % self.RAKLIB_TPS) == 0:
            if self.sendBytes > 0 or self.receiveBytes > 0:
                self._eventListener.onBandwidthStatsUpdate(self.sendBytes, self.receiveBytes)
                self.sendBytes = 0
                self.receiveBytes = 0

            packetErrorsWithoutMessage = self._packetErrorsSinceLastUpdate - self._packetErrorSuppressionThreshold
            if packetErrorsWithoutMessage > 0:
                self._logger.warning(
                    f"{packetErrorsWithoutMessage} suppressed packet errors - RakLib may be under attack"
                )
            self._packetErrorsSinceLastUpdate = 0

            ipsBlockedWithoutMessage = self._blockedSinceLastUpdate - self._blockMessageSuppressionThreshold
            if ipsBlockedWithoutMessage > 0:
                self._logger.warning(
                    f"{ipsBlockedWithoutMessage} more IP addresses were blocked - RakLib may be under attack"
                )
            self._blockedSinceLastUpdate = 0

            if len(self._block) > 0:
                now = int(time.time())
                for address in sorted(self._block, key=lambda a: self._block[a]):
                    timeout = self._block[address]
                    if timeout <= now:
                        del self._block[address]
                    else:
                        break

            if (
                self._cookieRotationIntervalTicks > 0
                and (self._ticks % self._cookieRotationIntervalTicks) == 0
            ):
                mismatches = self._unconnectedMessageHandler.getCookieMismatchSinceLastRotation()
                if mismatches > 0:
                    self._logger.warning(
                        f"Mismatched cookies detected {mismatches} times since last rotation - "
                        f"RakLib may be experiencing an attack from spoofed IP addresses"
                    )
                self._unconnectedMessageHandler.rotateCookieSalts()

        self._ticks += 1

    def _receivePacket(self) -> bool:
        try:
            buffer, addressIp, addressPort = self._socket.readPacket()
        except SocketException as e:
            error = e.code
            if error == errno.ECONNRESET:  # client disconnected improperly, maybe crash or lost connection
                return True
            self._logger.debug(str(e))
            return False

        if buffer is None:
            return False  # no data

        assert addressIp is not None and addressPort is not None

        length = len(buffer)

        self.receiveBytes += length
        if addressIp in self._block:
            return True

        if addressIp in self._ipSec:
            self._ipSec[addressIp] += 1
            if self._ipSec[addressIp] >= self._packetLimit:
                self.blockAddress(addressIp)
                return True
        else:
            self._ipSec[addressIp] = 1

        if length < 1:
            return True

        address = InternetAddress(addressIp, addressPort, self._socket.getBindAddress().getVersion())
        try:
            session = self.getSessionByAddress(address)
            if session is not None:
                header = buffer[0]
                if (header & Datagram.BITFLAG_VALID) != 0:
                    if (header & Datagram.BITFLAG_ACK) != 0:
                        packet = ACK()
                    elif (header & Datagram.BITFLAG_NAK) != 0:
                        packet = NACK()
                    else:
                        packet = Datagram()
                    packet.decode(PacketSerializer(buffer))
                    try:
                        session.handlePacket(packet)
                    except PacketHandlingException as e:
                        session.getLogger().error(f"Error receiving packet: {e}")
                        session.forciblyDisconnect(e.getDisconnectReason())
                    return True
                elif session.isConnected():
                    # allows unconnected packets if the session is stuck in DISCONNECTING state, useful if the
                    # client didn't disconnect properly for some reason (e.g. crash)
                    self._logger.debug(
                        f"Ignored unconnected packet from {address} due to session already opened "
                        f"(0x{buffer[0]:02x})"
                    )
                    return True

            if not self._shutdown:
                handled = self._unconnectedMessageHandler.handleRaw(buffer, address)
                if not handled:
                    for pattern in self._rawPacketRegexes:
                        if pattern.search(buffer):
                            handled = True
                            self._eventListener.onRawPacketReceive(address.getIp(), address.getPort(), buffer)
                            break

                if not handled:
                    self._logger.debug(
                        f"Ignored packet from {address} due to no session opened (0x{buffer[0]:02x})"
                    )
        except BinaryDataException as exception:
            if self._packetErrorsSinceLastUpdate < self._packetErrorSuppressionThreshold:
                def logFn(error: BaseException = exception) -> None:
                    self._logger.debug(f"Packet from {address} ({len(buffer)} bytes): 0x{buffer.hex()}")
                    self._logger.error(f"Bad packet from {address}: {error}")

                if isinstance(self._logger, BufferedLogger):
                    self._logger.buffer(logFn)
                else:
                    logFn()
            self._packetErrorsSinceLastUpdate += 1
            if self._blockIpOnPacketErrors:
                self.blockAddress(address.getIp(), 5)

        return True

    def sendPacket(self, packet: Packet, address: InternetAddress) -> None:
        out = PacketSerializer()
        packet.encode(out)
        try:
            self.sendBytes += self._socket.writePacket(out.getBuffer(), address.getIp(), address.getPort())
        except SocketException as e:
            self._logger.debug(str(e))

    def getEventListener(self):
        return self._eventListener

    def sendEncapsulated(self, sessionId: int, packet: EncapsulatedPacket, immediate: bool = False) -> None:
        session = self._sessions.get(sessionId)
        if session is not None and session.isConnected():
            session.addEncapsulatedToQueue(packet, immediate)

    def sendRaw(self, address: str, port: int, payload: bytes) -> None:
        try:
            self._socket.writePacket(payload, address, port)
        except SocketException as e:
            self._logger.debug(str(e))

    def closeSession(self, sessionId: int) -> None:
        if sessionId in self._sessions:
            self._sessions[sessionId].initiateDisconnect(DisconnectReason.SERVER_DISCONNECT)

    def setName(self, name: str) -> None:
        self._name = name

    def setPortCheck(self, value: bool) -> None:
        self.portChecking = value

    def setPacketsPerTickLimit(self, limit: int) -> None:
        self._packetLimit = limit

    def blockAddress(self, address: str, timeout: int = 300) -> None:
        final = int(time.time()) + timeout
        if address not in self._block or timeout == -1:
            if timeout == -1:
                final = _PHP_INT_MAX
            if self._blockedSinceLastUpdate < self._blockMessageSuppressionThreshold:
                # Suppress additional log messages if multiple IPs have been banned in quick succession
                # In the case of IP spoofing attacks we don't want log spam to slow down the server
                self._logger.notice(
                    f"Blocked {address}" + (" forever" if timeout == -1 else f" for {timeout} seconds")
                )
            self._block[address] = final
            self._blockedSinceLastUpdate += 1
        elif self._block[address] < final:
            self._block[address] = final

    def unblockAddress(self, address: str) -> None:
        self._block.pop(address, None)
        self._logger.debug(f"Unblocked {address}")

    def addRawPacketFilter(self, regex: str) -> None:
        self._rawPacketFilters.append(regex)
        self._rawPacketRegexes.append(re.compile(regex.encode() if isinstance(regex, str) else regex))

    def getSessionByAddress(self, address: InternetAddress) -> ServerSession | None:
        return self._sessionsByAddress.get(address.toString())

    def sessionExists(self, address: InternetAddress) -> bool:
        return address.toString() in self._sessionsByAddress

    def createSession(self, address: InternetAddress, clientId: int, mtuSize: int) -> ServerSession:
        existingSession = self._sessionsByAddress.get(address.toString())
        if existingSession is not None:
            existingSession.forciblyDisconnect(DisconnectReason.CLIENT_RECONNECT)
            self._removeSessionInternal(existingSession)

        self._checkSessions()

        while self._nextSessionId in self._sessions:
            self._nextSessionId += 1
            self._nextSessionId &= 0x7FFFFFFF  # fits in 4 bytes

        # clone the address (mirrors PHP's `clone $address`)
        sessionAddress = InternetAddress(address.getIp(), address.getPort(), address.getVersion())
        session = ServerSession(
            self,
            self._logger,
            sessionAddress,
            clientId,
            mtuSize,
            self._nextSessionId,
            self._recvMaxSplitParts,
            self._recvMaxConcurrentSplits,
        )
        self._sessionsByAddress[address.toString()] = session
        self._sessions[self._nextSessionId] = session
        self._logger.debug(f"Created session for {address} with MTU size {mtuSize}")

        return session

    def _removeSessionInternal(self, session: ServerSession) -> None:
        self._sessionsByAddress.pop(session.getAddress().toString(), None)
        self._sessions.pop(session.getInternalId(), None)

    def openSession(self, session: ServerSession) -> None:
        address = session.getAddress()
        self._eventListener.onClientConnect(
            session.getInternalId(), address.getIp(), address.getPort(), session.getID()
        )

    def _checkSessions(self) -> None:
        if len(self._sessions) > 4096:
            for sessionId in list(self._sessions.keys()):
                session = self._sessions[sessionId]
                if session.isTemporary():
                    self._removeSessionInternal(session)
                    if len(self._sessions) <= 4096:
                        break

    def getName(self) -> str:
        return self._name

    def getID(self) -> int:
        return self._serverId