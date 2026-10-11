# Contributing to PywRakLib

Thank you for your interest in contributing to PywRakLib. This document explains how to set up the project, run
tests, and submit changes.

## License

This project is a Python port of [pmmp/RakLib](https://github.com/pmmp/RakLib) and is licensed under the
**GNU General Public License v3.0**, including the PocketMine-MP-specific exception. See [LICENSE.md](LICENSE.md).

By contributing, you agree that your contributions will be licensed under the same terms. You must not submit
code that you do not have the right to license under GPL-3.0.

## Setting Up

1. Clone the repository:

   ```bash
   git clone https://github.com/MaybeRickSanchez/PywRakLib.git
   cd PywRakLib
   ```

2. Create a virtual environment and install in editable mode:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e .
   ```

## Running Tests

The test suite uses the standard library `unittest` framework:

```bash
python -m unittest discover -s tests -v
```

The tests include:

- **Golden wire-format vectors** — byte-for-byte comparisons against the original PHP implementation.
- **Binary serialization tests** — integer endianness, varints, and stream behavior.
- **Reliability layer tests** — ordering, reordering, and split-packet reassembly.
- **End-to-end integration test** — a real RakNet handshake over UDP against a running server instance.

All tests must pass before submitting a change.

## Code Style

- Follow the existing code style. The project uses 4-space indentation and `from __future__ import annotations`.
- Keep the directory structure and public API stable. This is a port; renaming or moving classes breaks compatibility.
- Do not add third-party dependencies. The library uses only the standard library.

## Submitting Changes

1. Fork the repository and create a feature branch.
2. Make your changes, ensuring all tests pass.
3. Update [CHANGELOG.md](CHANGELOG.md) if your change is user-visible.
4. Open a pull request with a clear description of the change and its motivation.

## Reporting Issues

Use the [issue tracker](https://github.com/MaybeRickSanchez/PywRakLib/issues) to report bugs or request features.
Please include:

- A description of the problem or request.
- Steps to reproduce (for bugs).
- The Python version and operating system you are using.