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

"""Accepts exactly one protocol version."""

from __future__ import annotations

from raklib.server.ProtocolAcceptor import ProtocolAcceptor


class SimpleProtocolAcceptor(ProtocolAcceptor):
    def __init__(self, protocolVersion: int):
        self._protocolVersion = protocolVersion

    def accepts(self, protocolVersion: int) -> bool:
        return self._protocolVersion == protocolVersion

    def getPrimaryVersion(self) -> int:
        return self._protocolVersion