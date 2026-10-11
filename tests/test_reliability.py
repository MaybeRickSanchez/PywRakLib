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

import unittest

from raklib.generic.ReceiveReliabilityLayer import ReceiveReliabilityLayer
from raklib.generic.SendReliabilityLayer import SendReliabilityLayer
from raklib.protocol.Datagram import Datagram
from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
from raklib.protocol.PacketReliability import PacketReliability
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.utils.log import Logger


class _NullLogger(Logger):
    def log(self, level, message):
        pass


MTU = 1400  # overhead 36 + 4 = 40 -> max payload 1360


class Loopback:
    """Wires a SendReliabilityLayer into a ReceiveReliabilityLayer over encoded datagrams."""

    def __init__(self, mtu=MTU):
        self.sent: list[bytes] = []
        self.received: list[bytes] = []
        self.acks: list[int] = []

        self.send = SendReliabilityLayer(
            mtu,
            self._captureDatagram,
            self.acks.append,
        )
        self.recv = ReceiveReliabilityLayer(
            _NullLogger(),
            lambda pk: self.received.append(pk.buffer),
            self._captureAck,
        )

    def _captureDatagram(self, datagram: Datagram) -> None:
        out = PacketSerializer()
        datagram.encode(out)
        self.sent.append(out.getBuffer())
        # feed it back into the receive side
        decoded = Datagram()
        decoded.decode(PacketSerializer(out.getBuffer()))
        self.recv.onDatagram(decoded)

    def _captureAck(self, packet) -> None:
        pass

    def flush(self) -> None:
        self.send.update()
        self.recv.update()


class ReliabilityTest(unittest.TestCase):
    def test_reliable_ordered_in_order(self):
        lb = Loopback()
        for i in range(10):
            pk = EncapsulatedPacket()
            pk.reliability = PacketReliability.RELIABLE_ORDERED
            pk.orderChannel = 0
            pk.buffer = bytes([i])
            lb.send.addEncapsulatedToQueue(pk, False)
        lb.flush()
        self.assertEqual([bytes([i]) for i in range(10)], lb.received)

    def test_unreliable_single(self):
        lb = Loopback()
        pk = EncapsulatedPacket()
        pk.reliability = PacketReliability.UNRELIABLE
        pk.buffer = b"hello"
        lb.send.addEncapsulatedToQueue(pk, True)
        self.assertEqual([b"hello"], lb.received)

    def test_split_reassembly(self):
        lb = Loopback()
        big = bytes(range(256)) * 40  # 10240 bytes, forces splitting
        pk = EncapsulatedPacket()
        pk.reliability = PacketReliability.RELIABLE_ORDERED
        pk.orderChannel = 0
        pk.buffer = big
        lb.send.addEncapsulatedToQueue(pk, False)
        lb.flush()
        self.assertEqual([big], lb.received)

    def test_ordered_out_of_order_reordering(self):
        # Build datagrams by hand and deliver them out of order.
        received: list[bytes] = []
        layer = ReceiveReliabilityLayer(
            _NullLogger(),
            lambda pk: received.append(pk.buffer),
            lambda packet: None,
        )

        serialized = []
        for order in range(3):
            pk = EncapsulatedPacket()
            pk.reliability = PacketReliability.RELIABLE_ORDERED
            pk.orderChannel = 0
            pk.orderIndex = order
            pk.messageIndex = order
            pk.buffer = bytes([order])
            serialized.append(pk)

        def deliver(orderIndex: int, seqNumber: int) -> None:
            d = Datagram()
            d.seqNumber = seqNumber
            d.packets = [serialized[orderIndex]]
            layer.onDatagram(d)

        deliver(0, 0)
        deliver(2, 1)
        self.assertEqual([b"\x00"], received)
        deliver(1, 2)
        self.assertEqual([b"\x00", b"\x01", b"\x02"], received)


if __name__ == "__main__":
    unittest.main()