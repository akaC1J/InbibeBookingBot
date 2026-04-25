from __future__ import annotations

from werkzeug.serving import BaseWSGIServer, make_server

from inbibe_bot.server.routes import ServerDeps, build_app


def build_server(deps: ServerDeps, port: int) -> BaseWSGIServer:
    app = build_app(deps)
    return make_server("0.0.0.0", port, app, threaded=True)
