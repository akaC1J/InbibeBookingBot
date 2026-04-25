from __future__ import annotations

import socketserver

from inbibe_bot.server.routes import ServerDeps, build_handler


def build_server(deps: ServerDeps, port: int) -> socketserver.TCPServer:
    handler_cls = build_handler(deps)
    server = socketserver.TCPServer(("", port), handler_cls)
    return server
