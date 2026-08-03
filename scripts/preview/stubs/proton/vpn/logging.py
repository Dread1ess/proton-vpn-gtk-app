"""
Minimal stand-in for the real ``proton.vpn.logging`` module (lives in the
private proton-vpn-core package). It is only used by the standalone preview
harness and must NOT be shipped or imported by the real app.
"""
import logging as _stdlib_logging


def getLogger(name: str):
    """Returns a standard library logger (mirrors the real getLogger)."""
    return _stdlib_logging.getLogger(name)


def config(filename: str = None, level=None, console: bool = True):  # noqa: A002
    """No-op placeholder for the real logging configuration."""
    if filename:
        _stdlib_logging.getLogger("preview").debug("logging.config(%r) ignored in preview", filename)
