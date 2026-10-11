# PywRakLib

__An unofficial Python port of [PocketMine-MP's RakLib](https://github.com/pmmp/RakLib) RakNet server library.__

PywRakLib is a UDP network library that implements the RakNet protocol. It is a direct Python translation of the
PHP implementation used by PocketMine-MP, preserving the original file structure, class names, public APIs, and
protocol behavior as closely as possible.

> **This is an unofficial port.** It is not an official PocketMine-MP release and is not affiliated with
> Jenkins Software LLC nor RakNet.

## Upstream

- **Original project:** [pmmp/RakLib](https://github.com/pmmp/RakLib)
- **Original language:** PHP
- **Port language:** Python
- **Port maintainer:** Amirreza Prime
- **Conversion baseline:** [`7655018`](https://github.com/pmmp/RakLib/commit/7655018631147f0b5d473326fddc2faea105dffe) (branch `stable`)

See [UPSTREAM.md](UPSTREAM.md) for full attribution and licensing details.

## Overview

PywRakLib is a port of the core RakNet server functionality provided by RakLib. It handles:

- The RakNet connection handshake (unconnected ping/pong, open connection request/reply)
- Reliable and unreliable packet delivery with ordering and sequencing
- Packet fragmentation and reassembly (split packets)
- ACK/NACK-based congestion control and retransmission
- Session lifecycle management (connect, disconnect, timeout)

The library is intentionally minimal — it does not implement most RakNet features and only provides server-side
functionality.

## Architecture

The package mirrors the original PHP namespaces:

| Python package       | PHP namespace      | Contents                                                        |
|----------------------|--------------------|-----------------------------------------------------------------|
| `raklib`             | `raklib`           | Library constants (`RakLib`)                                     |
| `raklib.utils`       | `raklib\utils`     | `InternetAddress`, binary streams, logging, trace cleaner        |
| `raklib.protocol`    | `raklib\protocol`  | All RakNet packets, `PacketSerializer`, `EncapsulatedPacket`    |
| `raklib.generic`     | `raklib\generic`   | `Socket`, `Session`, send/receive reliability layers             |
| `raklib.server`      | `raklib\server`    | `Server`, `ServerSession`, sockets and message handlers          |
| `raklib.client`      | `raklib\client`    | `ClientSocket`                                                   |

### Key design notes

- **Wire compatibility:** Packet serialization for the implemented packet types produces byte-for-byte identical
  output to the PHP implementation, as verified by golden-vector tests covering all packet classes, both IPv4 and
  IPv6 address encoding, and all reliability types.
- **Integer semantics:** PHP's 64-bit signed integers are emulated explicitly. `Binary.readLong()` and
  `readLLong()` wrap results into the signed 64-bit range, matching PHP behavior.
- **No external dependencies:** The library uses only the Python standard library. The bundled `pocketmine/log`
  and `pocketmine/binaryutils` PHP packages are replaced by compatible Python modules in `raklib.utils`.

## Features

- RakNet protocol handshake (unconnected ping/pong, open connection request/reply 1 and 2)
- Reliable, reliable-ordered, reliable-sequenced, unreliable, and unreliable-sequenced packet delivery
- Packet fragmentation and reassembly for messages exceeding the MTU
- ACK/NACK-based retransmission with configurable window sizes
- Session management with graceful and forcible disconnect
- IP-based rate limiting and blocking
- Anti-IP-spoofing cookies during the connection handshake
- IPv4 and IPv6 support
- Server-side only (no client implementation beyond the raw socket)

## Limitations

- **Server-side only.** There is no high-level client implementation; only `ClientSocket` is provided.
- **Minimal RakNet support.** Most RakNet features (NAT punchthrough, voice, plugins, etc.) are not implemented.
- **No encryption.** The libcat security / encryption challenge is not supported.
- **Single-threaded.** The server runs a single-threaded event loop via `tickProcessor()`.

## Requirements

- Python 3.10 or later
- No third-party runtime dependencies

## Installation

Install from source:

```bash
python -m pip install .
```

For development (editable install):

```bash
python -m pip install -e .
```

## Usage

Implement `ServerEventListener` and `ServerEventSource`, then drive the server with `tickProcessor()`:

```python
from raklib.server import Server, ServerSocket, SimpleProtocolAcceptor, ServerEventListener
from raklib.utils import InternetAddress, GlobalLogger, ExceptionTraceCleaner


class MyListener(ServerEventListener):
    def onClientConnect(self, sessionId, address, port, clientID):
        print(f"{address}:{port} connected")

    def onPacketReceive(self, sessionId, packet):
        print(f"Got {len(packet)} bytes")

    def onClientDisconnect(self, sessionId, reason):
        pass

    def onRawPacketReceive(self, address, port, payload):
        pass

    def onPacketAck(self, sessionId, identifierACK):
        pass

    def onBandwidthStatsUpdate(self, bytesSentDiff, bytesReceivedDiff):
        pass

    def onPingMeasure(self, sessionId, pingMS):
        pass


class MyEventSource:
    def process(self, server) -> bool:
        return False


server = Server(
    serverId=1234,
    logger=GlobalLogger.get(),
    socket=ServerSocket(InternetAddress("0.0.0.0", 19132, 4)),
    maxMtuSize=1492,
    protocolAcceptor=SimpleProtocolAcceptor(6),
    eventSource=MyEventSource(),
    eventListener=MyListener(),
    traceCleaner=ExceptionTraceCleaner(__file__),
)

while True:
    server.tickProcessor()
```

A complete runnable example is available in [`examples/echo_server.py`](examples/echo_server.py):

```bash
python examples/echo_server.py 0.0.0.0 19132
```

## Tools

Two command-line tools are included:

```bash
python tools/scan.py <broadcast-address> <port>    # broadcast RakNet pings and print pongs
python tools/proxy.py [server-address] [server-port]  # UDP proxy with cached ping responses
```

## Tests

The test suite includes golden wire-format vectors captured from the original PHP implementation for all
implemented packet types, both IPv4 and IPv6 address encoding, and all reliability types. An end-to-end
integration test performs a real RakNet handshake over UDP against a running server instance.

```bash
python -m unittest discover -s tests -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the GNU General Public License v3.0, the same license as the upstream project,
including the PocketMine-MP-specific exception. See [LICENSE.md](LICENSE.md) for the full text.

The original PHP implementation is Copyright (C) 2014-2022 PocketMine Team. This Python port is
Copyright (C) 2026 Amirreza Prime.

## Links

- [License](LICENSE.md)
- [Upstream project information](UPSTREAM.md)
- [Issue tracker](https://github.com/MaybeRickSanchez/PywRakLib/issues)
- [Changelog](CHANGELOG.md)
