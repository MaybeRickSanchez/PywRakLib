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

"""Handles outbound reliability: queueing, fragmentation, retransmission and ACK/NACK processing."""

from __future__ import annotations

import time
from typing import Callable

from raklib.generic.ReliableCacheEntry import ReliableCacheEntry
from raklib.protocol.ACK import ACK
from raklib.protocol.Datagram import Datagram
from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.NACK import NACK
from raklib.protocol.PacketReliability import PacketReliability
from raklib.protocol.SplitPacketInfo import SplitPacketInfo


_MIN_MTU_SIZE = 400  # mirrors generic.Session.MIN_MTU_SIZE without importing it (avoids a circular import)


class SendReliabilityLayer:
    DATAGRAM_MTU_OVERHEAD = 36 + Datagram.HEADER_SIZE  # IP (20) + UDP (8) + RakNet weird (8) = 36
    MIN_POSSIBLE_PACKET_SIZE_LIMIT = _MIN_MTU_SIZE - DATAGRAM_MTU_OVERHEAD

    # Delay in seconds before an unacked packet is retransmitted.
    UNACKED_RETRANSMIT_DELAY = 2.0

    def __init__(
        self,
        mtuSize: int,
        sendDatagramCallback: Callable[[Datagram], None],
        onACK: Callable[[int], None],
        reliableWindowSize: int = 512,
    ):
        self._mtuSize = mtuSize
        self._sendDatagramCallback = sendDatagramCallback
        self._onACK = onACK
        self._reliableWindowSize = reliableWindowSize

        self._sendQueue: list[EncapsulatedPacket] = []
        self._splitID = 0
        self._sendSeqNumber = 0
        self._messageIndex = 0

        self._reliableWindowStart = 0
        self._reliableWindowEnd = reliableWindowSize
        self._reliableWindow: dict[int, bool] = {}

        self._sendOrderedIndex = [0] * PacketReliability.MAX_ORDER_CHANNELS
        self._sendSequencedIndex = [0] * PacketReliability.MAX_ORDER_CHANNELS

        self._reliableBacklog: dict[int, EncapsulatedPacket] = {}
        self._resendQueue: list[EncapsulatedPacket] = []
        self._reliableCache: dict[int, ReliableCacheEntry] = {}
        self._needACK: dict[int, dict[int, int]] = {}

        self._maxDatagramPayloadSize = mtuSize - self.DATAGRAM_MTU_OVERHEAD

    def _sendDatagram(self, packets: list[EncapsulatedPacket]) -> None:
        datagram = Datagram()
        datagram.seqNumber = self._sendSeqNumber
        self._sendSeqNumber += 1
        datagram.packets = packets
        self._sendDatagramCallback(datagram)

        resendable = [pk for pk in datagram.packets if PacketReliability.isReliable(pk.reliability)]
        if len(resendable) != 0:
            self._reliableCache[datagram.seqNumber] = ReliableCacheEntry(resendable)

    def sendQueue(self) -> None:
        if len(self._sendQueue) > 0:
            self._sendDatagram(self._sendQueue)
            self._sendQueue = []

    def _addToQueue(self, pk: EncapsulatedPacket, immediate: bool) -> None:
        if PacketReliability.isReliable(pk.reliability):
            if pk.messageIndex is None or pk.messageIndex < self._reliableWindowStart:
                raise ValueError(
                    f"Cannot send a reliable packet with message index less than the window start "
                    f"({pk.messageIndex} < {self._reliableWindowStart})"
                )
            if pk.messageIndex >= self._reliableWindowEnd:
                # If we send this now, the client's reliable window may overflow, causing redelivery
                self._reliableBacklog[pk.messageIndex] = pk
                return

            self._reliableWindow[pk.messageIndex] = False

        if pk.identifierACK is not None and pk.messageIndex is not None:
            self._needACK.setdefault(pk.identifierACK, {})[pk.messageIndex] = pk.messageIndex

        length = 0
        for queued in self._sendQueue:
            length += queued.getTotalLength()

        if length + pk.getTotalLength() > self._maxDatagramPayloadSize:
            self.sendQueue()

        if pk.identifierACK is not None:
            clone = EncapsulatedPacket()
            clone.reliability = pk.reliability
            clone.messageIndex = pk.messageIndex
            clone.sequenceIndex = pk.sequenceIndex
            clone.orderIndex = pk.orderIndex
            clone.orderChannel = pk.orderChannel
            clone.splitInfo = pk.splitInfo
            clone.buffer = pk.buffer
            clone.identifierACK = pk.identifierACK
            self._sendQueue.append(clone)
            pk.identifierACK = None
        else:
            self._sendQueue.append(pk)

        if immediate:
            # Forces pending sends to go out now, rather than waiting to the next update interval
            self.sendQueue()

    def addEncapsulatedToQueue(self, packet: EncapsulatedPacket, immediate: bool = False) -> None:
        if packet.identifierACK is not None:
            self._needACK[packet.identifierACK] = {}

        if PacketReliability.isOrdered(packet.reliability):
            if packet.orderChannel is None:
                raise ValueError(f"Order channel must be set reliability {packet.reliability}")
            packet.orderIndex = self._sendOrderedIndex[packet.orderChannel]
            self._sendOrderedIndex[packet.orderChannel] += 1
        elif PacketReliability.isSequenced(packet.reliability):
            if packet.orderChannel is None:
                raise ValueError(f"Order channel must be set for reliability {packet.reliability}")
            # sequenced packets don't increment the ordered channel index
            packet.orderIndex = self._sendOrderedIndex[packet.orderChannel]
            packet.sequenceIndex = self._sendSequencedIndex[packet.orderChannel]
            self._sendSequencedIndex[packet.orderChannel] += 1

        maxBufferSize = self._maxDatagramPayloadSize - packet.getHeaderLength()

        if len(packet.buffer) > maxBufferSize:
            chunkSize = maxBufferSize - EncapsulatedPacket.SPLIT_INFO_LENGTH
            buffers = [packet.buffer[i:i + chunkSize] for i in range(0, len(packet.buffer), chunkSize)]
            bufferCount = len(buffers)

            self._splitID = (self._splitID + 1) % 65536
            splitID = self._splitID
            for count, buffer in enumerate(buffers):
                pk = EncapsulatedPacket()
                pk.splitInfo = SplitPacketInfo(splitID, count, bufferCount)
                pk.reliability = packet.reliability
                pk.buffer = buffer
                pk.identifierACK = packet.identifierACK

                if PacketReliability.isReliable(pk.reliability):
                    pk.messageIndex = self._messageIndex
                    self._messageIndex += 1

                pk.sequenceIndex = packet.sequenceIndex
                pk.orderChannel = packet.orderChannel
                pk.orderIndex = packet.orderIndex

                self._addToQueue(pk, True)
        else:
            if PacketReliability.isReliable(packet.reliability):
                packet.messageIndex = self._messageIndex
                self._messageIndex += 1
            self._addToQueue(packet, immediate)

    def _updateReliableWindow(self) -> None:
        while (
            self._reliableWindowStart in self._reliableWindow
            and self._reliableWindow[self._reliableWindowStart] is True
        ):
            del self._reliableWindow[self._reliableWindowStart]
            self._reliableWindowStart += 1
            self._reliableWindowEnd += 1

    def onACK(self, packet: ACK) -> None:
        for seq in packet.packets:
            if seq in self._reliableCache:
                for pk in self._reliableCache[seq].getPackets():
                    assert (
                        pk.messageIndex is not None
                        and pk.messageIndex >= self._reliableWindowStart
                        and pk.messageIndex < self._reliableWindowEnd
                    )
                    self._reliableWindow[pk.messageIndex] = True
                    self._updateReliableWindow()

                    if pk.identifierACK is not None:
                        ackMap = self._needACK.get(pk.identifierACK)
                        if ackMap is not None:
                            ackMap.pop(pk.messageIndex, None)
                        if not ackMap:
                            self._needACK.pop(pk.identifierACK, None)
                            self._onACK(pk.identifierACK)
                del self._reliableCache[seq]

    def onNACK(self, packet: NACK) -> None:
        for seq in packet.packets:
            if seq in self._reliableCache:
                for pk in self._reliableCache[seq].getPackets():
                    self._resendQueue.append(pk)
                del self._reliableCache[seq]

    def needsUpdate(self) -> bool:
        return (
            len(self._sendQueue) != 0
            or len(self._reliableBacklog) != 0
            or len(self._resendQueue) != 0
            or len(self._reliableCache) != 0
        )

    def update(self) -> None:
        retransmitOlderThan = time.time() - self.UNACKED_RETRANSMIT_DELAY
        for seq in list(self._reliableCache.keys()):
            pk = self._reliableCache[seq]
            if pk.getTimestamp() < retransmitOlderThan:
                # behave as if a NACK was received
                self._resendQueue.extend(pk.getPackets())
                del self._reliableCache[seq]
            else:
                break

        if len(self._resendQueue) > 0:
            for pk in self._resendQueue:
                # resends should always be within the reliable window
                self._addToQueue(pk, False)
            self._resendQueue = []

        if len(self._reliableBacklog) > 0:
            for k in list(self._reliableBacklog.keys()):
                pk = self._reliableBacklog[k]
                assert pk.messageIndex is not None and pk.messageIndex >= self._reliableWindowStart
                if pk.messageIndex >= self._reliableWindowEnd:
                    # we can't send this packet yet, the client's reliable window will drop it
                    break

                self._addToQueue(pk, False)
                del self._reliableBacklog[k]

        self.sendQueue()