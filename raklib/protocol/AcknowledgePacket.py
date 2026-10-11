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

"""Base class for ACK/NACK packets, using RakNet's range compression scheme."""

from __future__ import annotations

from raklib.protocol.Packet import Packet
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.utils.binary import Binary


class AcknowledgePacket(Packet):
    RECORD_TYPE_RANGE = 0
    RECORD_TYPE_SINGLE = 1

    def __init__(self):
        self.packets: list[int] = []

    def encodePayload(self, out: PacketSerializer) -> None:
        payload = bytearray()
        self.packets.sort()
        count = len(self.packets)
        records = 0

        if count > 0:
            pointer = 1
            start = self.packets[0]
            last = self.packets[0]

            while pointer < count:
                current = self.packets[pointer]
                pointer += 1
                diff = current - last
                if diff == 1:
                    last = current
                elif diff > 1:  # Forget about duplicated packets (bad queues?)
                    if start == last:
                        payload.append(self.RECORD_TYPE_SINGLE)
                        payload += Binary.writeLTriad(start)
                        start = last = current
                    else:
                        payload.append(self.RECORD_TYPE_RANGE)
                        payload += Binary.writeLTriad(start)
                        payload += Binary.writeLTriad(last)
                        start = last = current
                    records += 1

            if start == last:
                payload.append(self.RECORD_TYPE_SINGLE)
                payload += Binary.writeLTriad(start)
            else:
                payload.append(self.RECORD_TYPE_RANGE)
                payload += Binary.writeLTriad(start)
                payload += Binary.writeLTriad(last)
            records += 1

        out.putShort(records)
        out.put(bytes(payload))

    def decodePayload(self, in_: PacketSerializer) -> None:
        count = in_.getShort()
        self.packets = []
        cnt = 0
        for _ in range(count):
            if in_.feof() or cnt >= 4096:
                break
            if in_.getByte() == self.RECORD_TYPE_RANGE:
                start = in_.getLTriad()
                end = in_.getLTriad()
                if (end - start) > 512:
                    end = start + 512
                for c in range(start, end + 1):
                    self.packets.append(c)
                    cnt += 1
            else:
                self.packets.append(in_.getLTriad())
                cnt += 1