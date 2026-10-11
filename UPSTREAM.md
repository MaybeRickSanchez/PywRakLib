# Upstream Project

This project is an **unofficial Python port** of [PocketMine-MP's RakLib](https://github.com/pmmp/RakLib).

## Original Repository

- **URL:** https://github.com/pmmp/RakLib
- **Maintainer:** PocketMine Team
- **License:** GNU General Public License v3.0 (GPL-3.0), with a PocketMine-MP-specific exception

## Source and Target Languages

- **Source language:** PHP
- **Target language:** Python

## Relationship to the Original

This project is a direct, file-by-file translation of the PHP implementation into Python. The directory structure,
class names, public APIs, protocol behavior, and algorithms are preserved as closely as possible to the original.
The goal is byte-for-byte wire compatibility with the upstream implementation.

This is **not** an independently implemented library, and it is **not** an official PocketMine-MP release. It is a
community-maintained port.

## Conversion Baseline

The conversion was based on the following upstream revision:

- **Commit:** `7655018631147f0b5d473326fddc2faea105dffe`
- **Branch:** `stable`
- **Date:** 2025-12-29
- **Subject:** "Add support for anti spoofing cookies"

This commit was the HEAD of the `stable` branch at the time the port was created. The port has not been
systematically re-validated against later upstream changes.

## Copyright and Licensing

- The original PHP implementation is Copyright (C) 2014-2022 PocketMine Team.
- The Python port is Copyright (C) 2026 Amirreza Prime.

This project is licensed under the **GNU General Public License v3.0**, the same license as the upstream project,
including the PocketMine-MP-specific exception. See [LICENSE.md](LICENSE.md) for the full license text and exception.

The upstream exception is reproduced exactly as supplied by the original project. It grants special permission for
use with PocketMine-MP and their plugins. This exception does **not** automatically apply to unrelated projects.
