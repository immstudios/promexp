__all__ = ["UServer"]

import inspect
import logging
import wsgiref.simple_server

from .request import VRequest
from .response import VResponse


class Vial():
    def __init__(self, app_name="Vial"):
        self.response = VResponse()
        self.app_name = app_name
        self.logger = logging.getLogger(app_name)

    def __call__(self, environ, respond):
        request = VRequest(environ)
        status, headers, body = self.handle(request)
        respond(status, headers)
        if inspect.isgeneratorfunction(body):
            yield from body
        else:
            yield body

    def handle(self, request):
        return self.response.text("Vial.handle is not implemented", 500)

    def serve(self, host="", port="8080"):
        self.logger.info(f"Starting dev server at {host}:{port}")
        server = wsgiref.simple_server.make_server(host, port, self)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down.")
            server.server_close()