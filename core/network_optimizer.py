"""High-speed Network & Socket Optimizer for Google Photos ReVanced Windows Edition.
Optimizes TCP window scaling, socket send buffers, HTTP chunk blocksize,
and persistent HTTP keep-alive connection pooling for 1Gbps+ fiber connections.
"""

import os
import sys
import socket
import http.client
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3.connection

_applied = False


class PersistentSessionProxy:
    """A proxy wrapper around requests.Session that prevents context-manager closure.
    Reuses open TCP/TLS connections across multiple API calls and file uploads.
    """

    def __init__(self, session: requests.Session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Do not close the session or tear down the TLS connection pool!
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


def apply_network_optimizations() -> None:
    """Apply high-performance socket, HTTP blocksize, and session pooling patches."""
    global _applied
    if _applied:
        return
    _applied = True

    # 1. Expand Winsock TCP Buffer & Enable TCP_NODELAY (Wire Speed 1Gbps)
    try:
        sock_opts = list(getattr(urllib3.connection.HTTPConnection, "default_socket_options", []))
        # Remove any previous socket buffer options
        sock_opts = [opt for opt in sock_opts if opt[1] not in (socket.SO_SNDBUF, socket.SO_RCVBUF)]
        # Force TCP_NODELAY
        sock_opts.append((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1))
        # 2MB Send Buffer for high bandwidth-delay product (BDP) on Windows
        sock_opts.append((socket.SOL_SOCKET, socket.SO_SNDBUF, 2 * 1024 * 1024))
        # 1MB Receive Buffer
        sock_opts.append((socket.SOL_SOCKET, socket.SO_RCVBUF, 1 * 1024 * 1024))
        urllib3.connection.HTTPConnection.default_socket_options = sock_opts
    except Exception:
        pass

    # 2. Elevate HTTP Stream Blocksize to 1MB (Reduces Python GIL / system call overhead by 128x)
    try:
        _orig_http_init = http.client.HTTPConnection.__init__

        def _fast_http_init(self, *args, **kwargs):
            if "blocksize" not in kwargs or kwargs["blocksize"] == 8192:
                kwargs["blocksize"] = 1024 * 1024  # 1MB read chunks for streaming uploads
            _orig_http_init(self, *args, **kwargs)

        http.client.HTTPConnection.__init__ = _fast_http_init
    except Exception:
        pass

    # 3. Patch GPMC Api to reuse persistent Keep-Alive connections
    try:
        import gpmc.api

        _orig_api_init = gpmc.api.Api.__init__

        def _patched_api_init(self, *args, **kwargs):
            _orig_api_init(self, *args, **kwargs)
            # Create a shared long-lived session with 64 connections pool
            s = requests.Session()
            retries = Retry(total=gpmc.api.RETRIES, backoff_factor=1, status_forcelist=[502, 503, 504])
            adapter = HTTPAdapter(
                pool_connections=64,
                pool_maxsize=64,
                max_retries=retries,
            )
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            s.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
            if self.proxy:
                s.verify = False
            self._shared_session_proxy = PersistentSessionProxy(s)

        def _patched_new_session(self) -> requests.Session:
            if hasattr(self, "_shared_session_proxy"):
                return self._shared_session_proxy
            # Fallback
            s = requests.Session()
            adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32)
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            return PersistentSessionProxy(s)

        gpmc.api.Api.__init__ = _patched_api_init
        gpmc.api.Api._new_session = _patched_new_session
    except Exception:
        pass
