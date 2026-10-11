# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- Initial Python port of [pmmp/RakLib](https://github.com/pmmp/RakLib) (baseline: commit `7655018`, branch `stable`).
- Port of the core RakNet server functionality: unconnected ping/pong, open connection request/reply 1 and 2,
  connection request/accept, and new incoming connection.
- Reliability layer with reliable, reliable-ordered, reliable-sequenced, unreliable, and unreliable-sequenced
  delivery.
- Packet fragmentation and reassembly (split packets).
- ACK/NACK-based retransmission.
- Session lifecycle management with graceful and forcible disconnect.
- IP-based rate limiting and blocking.
- Anti-IP-spoofing cookies during the connection handshake.
- IPv4 and IPv6 support.
- `raklib.utils.binary` module replacing `pocketmine/binaryutils`.
- `raklib.utils.log` module replacing `pocketmine/log`.
- Command-line tools: `tools/scan.py` and `tools/proxy.py`.
- Example server: `examples/echo_server.py`.
- Test suite with golden wire-format vectors and an end-to-end UDP handshake integration test.

### Notes

- This is the first release of the Python port. It has not been published to PyPI.
- The port is based on upstream commit `7655018631147f0b5d473326fddc2faea105dffe` and has not been
  systematically re-validated against later upstream changes.