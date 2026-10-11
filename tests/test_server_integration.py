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

import socket
import threading
import time
import unittest

from raklib.protocol.MessageIdentifiers import MessageIdentifiers
from raklib.protocol.PacketSerializer import PacketSerializer
from raklib.protocol.UnconnectedPing import UnconnectedPing
from raklib.protocol.UnconnectedPong import UnconnectedPong
from raklib.server.Server import Server
from raklib.server.ServerEventListener import ServerEventListener
from raklib.server.ServerSocket import ServerSocket
from raklib.server.SimpleProtocolAcceptor import SimpleProtocolAcceptor
from raklib.utils.ExceptionTraceCleaner import ExceptionTraceCleaner
from raklib.utils.InternetAddress import InternetAddress
from raklib.utils.log import Logger, LogLevel


class _NullLogger(Logger):
    def log(self, level, message):
        pass


class _RecordingListener(ServerEventListener):
    def __init__(self):
        self.connected = []
        self.received = []

    def onClientConnect(self, sessionId, address, port, clientID):
        self.connected.append((sessionId, address, port, clientID))

    def onClientDisconnect(self, sessionId, reason):
        pass

    def onPacketReceive(self, sessionId, packet):
        self.received.append(packet)

    def onRawPacketReceive(self, address, port, payload):
        pass

    def onPacketAck(self, sessionId, identifierACK):
        pass

    def onBandwidthStatsUpdate(self, bytesSentDiff, bytesReceivedDiff):
        pass

    def onPingMeasure(self, sessionId, pingMS):
        pass


class _TrivialEventSource:
    """Immediately signals that there are no events to process."""

    def process(self, server):
        return False


class _ServerThread(threading.Thread):
    def __init__(self, server):
        super().__init__(daemon=True)
        self.server = server
        self.stopFlag = False

    def run(self):
        while not self.stopFlag and not self.server._shutdown:
            self.server.tickProcessor()

    def stop(self):
        self.stopFlag = True


def _freePort() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ServerIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.port = _freePort()
        self.listener = _RecordingListener()
        self.server = Server(
            serverId=1234,
            logger=_NullLogger(LogLevel.WARNING),
            socket=ServerSocket(InternetAddress("127.0.0.1", self.port, 4)),
            maxMtuSize=1400,
            protocolAcceptor=SimpleProtocolAcceptor(6),
            eventSource=_TrivialEventSource(),
            eventListener=self.listener,
            traceCleaner=ExceptionTraceCleaner("/"),
        )
        self.server.setName("MCPE;Test Server;")
        self.thread = _ServerThread(self.server)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.thread.stop()
        self.server._shutdown = True
        self.thread.join(timeout=2)
        try:
            self.server._socket.close()
        except OSError:
            pass

    def test_unconnected_ping_gets_pong(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(2)
        try:
            ping = UnconnectedPing()
            ping.sendPingTime = 4242
            ping.clientId = 99
            serializer = PacketSerializer()
            ping.encode(serializer)
            client.sendto(serializer.getBuffer(), ("127.0.0.1", self.port))

            data, _ = client.recvfrom(65535)
            self.assertEqual(MessageIdentifiers.ID_UNCONNECTED_PONG, data[0])

            pong = UnconnectedPong()
            pong.decode(PacketSerializer(data))
            self.assertEqual(4242, pong.sendPingTime)
            self.assertEqual(1234, pong.serverId)
            self.assertEqual(b"MCPE;Test Server;", pong.serverName)
        finally:
            client.close()

    def test_full_handshake(self):
        from raklib.protocol.ConnectionRequest import ConnectionRequest
        from raklib.protocol.NewIncomingConnection import NewIncomingConnection
        from raklib.protocol.OpenConnectionRequest1 import OpenConnectionRequest1
        from raklib.protocol.OpenConnectionRequest2 import OpenConnectionRequest2
        from raklib.protocol.OpenConnectionReply1 import OpenConnectionReply1
        from raklib.protocol.OpenConnectionReply2 import OpenConnectionReply2
        from raklib.protocol.Datagram import Datagram
        from raklib.protocol.EncapsulatedPacket import EncapsulatedPacket
        from raklib.protocol.PacketReliability import PacketReliability

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(2)
        addr = ("127.0.0.1", self.port)

        def send(pk):
            s = PacketSerializer()
            pk.encode(s)
            client.sendto(s.getBuffer(), addr)

        try:
            # Step 1: OpenConnectionRequest1 (MTU negotiation)
            r1 = OpenConnectionRequest1()
            r1.protocol = 6
            r1.mtuSize = 1400
            send(r1)

            data, _ = client.recvfrom(65535)
            reply1 = OpenConnectionReply1()
            reply1.decode(PacketSerializer(data))
            self.assertEqual(1234, reply1.serverID)
            self.assertIsNotNone(reply1.cookie)

            # Step 2: OpenConnectionRequest2 (with cookie)
            r2 = OpenConnectionRequest2()
            r2.clientID = 555
            r2.serverAddress = InternetAddress("127.0.0.1", self.port, 4)
            r2.mtuSize = 1400
            r2.cookie = reply1.cookie
            send(r2)

            data, _ = client.recvfrom(65535)
            reply2 = OpenConnectionReply2()
            reply2.decode(PacketSerializer(data))
            self.assertEqual(1234, reply2.serverID)

            # Step 3: ConnectionRequest inside a datagram, wrapped reliably
            def send_reliable(binary, seq, messageIndex, orderIndex):
                ep = EncapsulatedPacket()
                ep.reliability = PacketReliability.RELIABLE_ORDERED
                ep.messageIndex = messageIndex
                ep.orderIndex = orderIndex
                ep.orderChannel = 0
                ep.buffer = binary
                d = Datagram()
                d.seqNumber = seq
                d.packets = [ep]
                s = PacketSerializer()
                d.encode(s)
                client.sendto(s.getBuffer(), addr)

            cr = ConnectionRequest()
            cr.clientID = 555
            cr.sendPingTime = 1000
            cr.useSecurity = False
            s = PacketSerializer()
            cr.encode(s)
            send_reliable(s.getBuffer(), 0, 0, 0)

            # server should reply ConnectionRequestAccepted (reliable-ordered) and ACK the datagram
            acksReceived = 0
            gotCRA = False
            deadline = time.time() + 2
            while time.time() < deadline and not (gotCRA and acksReceived >= 1):
                try:
                    data, _ = client.recvfrom(65535)
                except socket.timeout:
                    break
                header = data[0]
                if (header & Datagram.BITFLAG_VALID) == 0:
                    continue
                if (header & Datagram.BITFLAG_ACK) != 0:
                    acksReceived += 1
                    continue
                d = Datagram()
                d.decode(PacketSerializer(data))
                for ep in d.packets:
                    if len(ep.buffer) > 0 and ep.buffer[0] == MessageIdentifiers.ID_CONNECTION_REQUEST_ACCEPTED:
                        gotCRA = True

            self.assertTrue(gotCRA, "Did not receive ConnectionRequestAccepted")
            self.assertGreaterEqual(acksReceived, 1, "Server did not ACK the ConnectionRequest datagram")

            # Step 4: NewIncomingConnection -> session becomes connected
            nic = NewIncomingConnection()
            nic.address = InternetAddress("127.0.0.1", self.port, 4)
            nic.systemAddresses = []
            nic.sendPingTime = 5
            nic.sendPongTime = 6
            s = PacketSerializer()
            nic.encode(s)
            send_reliable(s.getBuffer(), 1, 1, 1)
            time.sleep(0.2)

            self.assertEqual(1, len(self.listener.connected))
            self.assertEqual(555, self.listener.connected[0][3])
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()