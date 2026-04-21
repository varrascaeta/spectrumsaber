"""
SpectrumSaber client — backward-compatible re-export shim.

All classes and entry points are now defined in dedicated sub-modules:
  spectrumsaber.ftp_client   — FTPClient, TimeoutException, TimeoutContext
  spectrumsaber.saber_client — SpectrumSaberClient
  spectrumsaber.interactive  — InteractiveClient, RichInteractiveClient
  spectrumsaber.cli          — CLIClient, main, main_t2gql

Low-level names (signal, FTP, requests) are imported here so that
``patch("spectrumsaber.client.<name>")`` targets work in tests.
"""

# Standard imports — exposed so test patches on spectrumsaber.client.* work
import signal  # noqa: F401
from ftplib import FTP  # noqa: F401

# Third-party imports — exposed for patching
import requests  # noqa: F401

from spectrumsaber.ftp_client import (
    DIR_LIST_PATTERN,
    FTPClient,
    TimeoutContext,
    TimeoutException,
)
from spectrumsaber.interactive import InteractiveClient, RichInteractiveClient
from spectrumsaber.saber_client import SpectrumSaberClient

__all__ = [
    "DIR_LIST_PATTERN",
    "FTPClient",
    "TimeoutContext",
    "TimeoutException",
    "SpectrumSaberClient",
    "InteractiveClient",
    "RichInteractiveClient",
]
