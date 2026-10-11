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

"""Reasons a session may be disconnected, ported from RakLib's ``DisconnectReason``."""

from __future__ import annotations


class DisconnectReason:
    CLIENT_DISCONNECT = 0
    SERVER_DISCONNECT = 1
    PEER_TIMEOUT = 2
    CLIENT_RECONNECT = 3
    SERVER_SHUTDOWN = 4
    SPLIT_PACKET_TOO_LARGE = 5
    SPLIT_PACKET_TOO_MANY_CONCURRENT = 6
    SPLIT_PACKET_INVALID_PART_INDEX = 7
    SPLIT_PACKET_INCONSISTENT_HEADER = 8

    _NAMES = {
        CLIENT_DISCONNECT: "client disconnect",
        SERVER_DISCONNECT: "server disconnect",
        PEER_TIMEOUT: "timeout",
        CLIENT_RECONNECT: "new session established on same address and port",
        SERVER_SHUTDOWN: "server shutdown",
        SPLIT_PACKET_TOO_LARGE: "received packet split into more parts than allowed",
        SPLIT_PACKET_TOO_MANY_CONCURRENT: "too many received split packets being reassembled at once",
        SPLIT_PACKET_INVALID_PART_INDEX: "invalid split packet part index",
        SPLIT_PACKET_INCONSISTENT_HEADER: "received split packet header inconsistent with previous fragments",
    }

    @staticmethod
    def toString(reason: int) -> str:
        return DisconnectReason._NAMES.get(reason, f"Unknown reason {reason}")