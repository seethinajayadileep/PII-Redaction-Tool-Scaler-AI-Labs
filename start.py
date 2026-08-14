"""Production server for Railway and Docker."""

from __future__ import annotations

import os
import socket

from uvicorn import Config, Server


def _listen(family: int, address: str, port: int) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind((address, port))
    sock.listen(2048)
    sock.set_inheritable(True)
    return sock


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    sockets: list[socket.socket] = []
    # Railway healthchecks and the public URL use IPv4.
    # Private networking uses IPv6. Uvicorn's --host flag can only do one.
    for family, address in (
        (socket.AF_INET, "0.0.0.0"),
        (socket.AF_INET6, "::"),
    ):
        try:
            sockets.append(_listen(family, address, port))
            print(f"Listening on {address}:{port}", flush=True)
        except OSError as exc:
            print(f"Could not bind {address}:{port}: {exc}", flush=True)
    if not sockets:
        raise SystemExit("Could not bind IPv4 or IPv6")
    config = Config(
        "app:app",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    Server(config).run(sockets=sockets)
