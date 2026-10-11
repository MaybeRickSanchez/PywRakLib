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

"""RakNet packet reliabilities, ported from RakLib's ``PacketReliability``."""

from __future__ import annotations


class PacketReliability:
    # From https://github.com/OculusVR/RakNet/blob/master/Source/PacketPriority.h
    # Default: 0b010 (2) or 0b011 (3)

    UNRELIABLE = 0
    UNRELIABLE_SEQUENCED = 1
    RELIABLE = 2
    RELIABLE_ORDERED = 3
    RELIABLE_SEQUENCED = 4

    # The following reliabilities are used in RakNet internals, but never sent on the wire.
    UNRELIABLE_WITH_ACK_RECEIPT = 5
    RELIABLE_WITH_ACK_RECEIPT = 6
    RELIABLE_ORDERED_WITH_ACK_RECEIPT = 7

    MAX_ORDER_CHANNELS = 32

    @staticmethod
    def isReliable(reliability: int) -> bool:
        return reliability in (
            PacketReliability.RELIABLE,
            PacketReliability.RELIABLE_ORDERED,
            PacketReliability.RELIABLE_SEQUENCED,
            PacketReliability.RELIABLE_WITH_ACK_RECEIPT,
            PacketReliability.RELIABLE_ORDERED_WITH_ACK_RECEIPT,
        )

    @staticmethod
    def isSequenced(reliability: int) -> bool:
        return reliability in (
            PacketReliability.UNRELIABLE_SEQUENCED,
            PacketReliability.RELIABLE_SEQUENCED,
        )

    @staticmethod
    def isOrdered(reliability: int) -> bool:
        return reliability in (
            PacketReliability.RELIABLE_ORDERED,
            PacketReliability.RELIABLE_ORDERED_WITH_ACK_RECEIPT,
        )

    @staticmethod
    def isSequencedOrOrdered(reliability: int) -> bool:
        return reliability in (
            PacketReliability.UNRELIABLE_SEQUENCED,
            PacketReliability.RELIABLE_ORDERED,
            PacketReliability.RELIABLE_SEQUENCED,
            PacketReliability.RELIABLE_ORDERED_WITH_ACK_RECEIPT,
        )