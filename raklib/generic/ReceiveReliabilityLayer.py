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

"""Handles inbound reliability: deduplication, ordering, split reassembly and ACK/NACK generation."""

from __future__ import annotations

from typing import Callable

from raklib.generic.DisconnectReason import DisconnectReason
from raklib.generic.PacketHandlingException import PacketHandlingException
from raklib.protocol.ACK import ACK
from raklib.protocol.AcknowledgePacket import AcknowledgePacket
from raklib.protocol.Datagram import Datagram
from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.NACK import NACK
from raklib.protocol.PacketReliability import PacketReliability
from raklib.utils.log import Logger


class ReceiveReliabilityLayer:
    WINDOW_SIZE = 2048

    def __init__(
        self,
        logger: Logger,
        onRecv: Callable[[EncapsulatedPacket], None],
        sendPacket: Callable[[AcknowledgePacket], None],
        maxSplitPacketPartCount: int = 2 ** 63 - 1,
        maxConcurrentSplitPackets: int = 2 ** 63 - 1,
    ):
        self._logger = logger
        self._onRecv = onRecv
        self._sendPacket = sendPacket
        self._maxSplitPacketPartCount = maxSplitPacketPartCount
        self._maxConcurrentSplitPackets = maxConcurrentSplitPackets

        self._windowStart = 0
        self._windowEnd = self.WINDOW_SIZE
        self._highestSeqNumber = -1

        self._ACKQueue: list[int] = []
        self._NACKQueue: list[int] = []

        self._reliableWindowStart = 0
        self._reliableWindowEnd = self.WINDOW_SIZE
        self._reliableWindow: set[int] = set()

        self._receiveOrderedIndex = [0] * PacketReliability.MAX_ORDER_CHANNELS
        self._receiveSequencedHighestIndex = [0] * PacketReliability.MAX_ORDER_CHANNELS
        self._receiveOrderedPackets: list[dict[int, EncapsulatedPacket]] = [
            {} for _ in range(PacketReliability.MAX_ORDER_CHANNELS)
        ]

        self._splitPackets: dict[int, list[EncapsulatedPacket | None]] = {}

    def _handleEncapsulatedPacketRoute(self, pk: EncapsulatedPacket) -> None:
        self._onRecv(pk)

    def _handleSplit(self, packet: EncapsulatedPacket) -> EncapsulatedPacket | None:
        if packet.splitInfo is None:
            return packet
        totalParts = packet.splitInfo.getTotalPartCount()
        partIndex = packet.splitInfo.getPartIndex()
        if totalParts >= self._maxSplitPacketPartCount or totalParts < 0:
            raise PacketHandlingException(
                f"Invalid split packet part count ({totalParts})",
                DisconnectReason.SPLIT_PACKET_TOO_LARGE,
            )
        if partIndex >= totalParts or partIndex < 0:
            raise PacketHandlingException(
                f"Invalid split packet part index (part index {partIndex}, part count {totalParts})",
                DisconnectReason.SPLIT_PACKET_INVALID_PART_INDEX,
            )

        splitId = packet.splitInfo.getId()
        if splitId not in self._splitPackets:
            if len(self._splitPackets) >= self._maxConcurrentSplitPackets:
                raise PacketHandlingException(
                    f"Exceeded concurrent split packet reassembly limit of {self._maxConcurrentSplitPackets}",
                    DisconnectReason.SPLIT_PACKET_TOO_MANY_CONCURRENT,
                )
            self._splitPackets[splitId] = [None] * totalParts
        elif len(self._splitPackets[splitId]) != totalParts:
            raise PacketHandlingException(
                f"Wrong split count {totalParts} for split packet {splitId}, "
                f"expected {len(self._splitPackets[splitId])}",
                DisconnectReason.SPLIT_PACKET_INCONSISTENT_HEADER,
            )

        self._splitPackets[splitId][partIndex] = packet

        parts = self._splitPackets[splitId]
        for part in parts:
            if part is None:
                return None

        # got all parts, reassemble the packet
        pk = EncapsulatedPacket()
        pk.buffer = b""

        pk.reliability = packet.reliability
        pk.messageIndex = packet.messageIndex
        pk.sequenceIndex = packet.sequenceIndex
        pk.orderIndex = packet.orderIndex
        pk.orderChannel = packet.orderChannel

        for i in range(totalParts):
            pk.buffer += parts[i].buffer

        del self._splitPackets[splitId]

        return pk

    def _handleEncapsulatedPacket(self, packet: EncapsulatedPacket) -> None:
        if packet.messageIndex is not None:
            # check for duplicates or out of range
            if (
                packet.messageIndex < self._reliableWindowStart
                or packet.messageIndex > self._reliableWindowEnd
                or packet.messageIndex in self._reliableWindow
            ):
                return

            self._reliableWindow.add(packet.messageIndex)

            if packet.messageIndex == self._reliableWindowStart:
                while self._reliableWindowStart in self._reliableWindow:
                    self._reliableWindow.discard(self._reliableWindowStart)
                    self._reliableWindowStart += 1
                    self._reliableWindowEnd += 1

        packet = self._handleSplit(packet)
        if packet is None:
            return

        if PacketReliability.isSequencedOrOrdered(packet.reliability) and (
            packet.orderChannel is None
            or packet.orderChannel < 0
            or packet.orderChannel >= PacketReliability.MAX_ORDER_CHANNELS
        ):
            # TODO: this should result in peer banning
            self._logger.debug(f"Invalid packet, bad order channel ({packet.orderChannel})")
            return

        if PacketReliability.isSequenced(packet.reliability):
            assert packet.orderChannel is not None and packet.sequenceIndex is not None
            if (
                packet.sequenceIndex < self._receiveSequencedHighestIndex[packet.orderChannel]
                or packet.orderIndex < self._receiveOrderedIndex[packet.orderChannel]
            ):
                # too old sequenced packet, discard it
                return

            self._receiveSequencedHighestIndex[packet.orderChannel] = packet.sequenceIndex + 1
            self._handleEncapsulatedPacketRoute(packet)
        elif PacketReliability.isOrdered(packet.reliability):
            orderChannel = packet.orderChannel
            assert orderChannel is not None
            if packet.orderIndex == self._receiveOrderedIndex[orderChannel]:
                # this is the packet we expected to get next
                self._receiveSequencedHighestIndex[orderChannel] = 0
                self._receiveOrderedIndex[orderChannel] = packet.orderIndex + 1

                self._handleEncapsulatedPacketRoute(packet)
                i = self._receiveOrderedIndex[orderChannel]
                pending = self._receiveOrderedPackets[orderChannel]
                while i in pending:
                    self._handleEncapsulatedPacketRoute(pending[i])
                    del pending[i]
                    i += 1

                self._receiveOrderedIndex[orderChannel] = i
            elif packet.orderIndex > self._receiveOrderedIndex[orderChannel]:
                if len(self._receiveOrderedPackets[orderChannel]) >= self.WINDOW_SIZE:
                    # queue overflow for this channel - we should probably disconnect the peer at this point
                    return
                self._receiveOrderedPackets[orderChannel][packet.orderIndex] = packet
            else:
                # duplicate/already received packet
                pass
        else:
            # not ordered or sequenced
            self._handleEncapsulatedPacketRoute(packet)

    def onDatagram(self, packet: Datagram) -> None:
        if (
            packet.seqNumber < self._windowStart
            or packet.seqNumber > self._windowEnd
            or packet.seqNumber in self._ACKQueue
        ):
            self._logger.debug(
                f"Received duplicate or out-of-window packet (sequence number {packet.seqNumber}, "
                f"window {self._windowStart}-{self._windowEnd})"
            )
            return

        if packet.seqNumber in self._NACKQueue:
            self._NACKQueue.remove(packet.seqNumber)
        self._ACKQueue.append(packet.seqNumber)
        if self._highestSeqNumber < packet.seqNumber:
            self._highestSeqNumber = packet.seqNumber

        if packet.seqNumber == self._windowStart:
            # got a contiguous packet, shift the receive window
            while self._windowStart in self._ACKQueue:
                self._windowStart += 1
                self._windowEnd += 1
        elif packet.seqNumber > self._windowStart:
            # we got a gap - a later packet arrived before earlier ones did
            for i in range(self._windowStart, packet.seqNumber):
                if i not in self._ACKQueue:
                    self._NACKQueue.append(i)
        else:
            assert False, "received packet before window start"

        for pk in packet.packets:
            self._handleEncapsulatedPacket(pk)

    def update(self) -> None:
        diff = self._highestSeqNumber - self._windowStart + 1
        assert diff >= 0
        if diff > 0:
            # Move the receive window to account for packets we either received or are about to NACK
            self._windowStart += diff
            self._windowEnd += diff

        if len(self._ACKQueue) > 0:
            pk = ACK()
            pk.packets = self._ACKQueue
            self._sendPacket(pk)
            self._ACKQueue = []

        if len(self._NACKQueue) > 0:
            pk = NACK()
            pk.packets = self._NACKQueue
            self._sendPacket(pk)
            self._NACKQueue = []

    def needsUpdate(self) -> bool:
        return len(self._ACKQueue) != 0 or len(self._NACKQueue) != 0