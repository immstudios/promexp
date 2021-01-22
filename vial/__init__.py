__all__ = ["Vial"]

import sys
import inspect
import logging
import traceback
import wsgiref.simple_server

from .request import VRequest
from .response import VResponse


def format_traceback():
    exc_type, exc_value, tb = sys.exc_info()
    result = "Traceback:\n\n    " +  "    ".join(traceback.format_exception(exc_type, exc_value, tb)[1:])
    return result


class VialRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    def log_message(self, format, *args):
        if not self.server.parent.log_requests:
            return
        req, resp, _ = args
        self.server.parent.logger.debug(f"[{resp}] {req} from {self.client_address[0]}")


class Vial():
    def __init__(self, app_name="Vial", logger=None, log_requests=True):
        self.response = VResponse()
        self.app_name = app_name
        self.log_requests = log_requests
        self._logger = logger

    @property
    def logger(self):
        if not self._logger:
            self._logger = logging.getLogger(self.app_name)
        return self._logger

    def __call__(self, environ, respond):
        request = VRequest(environ)
        try:
            status, headers, body = self.handle(request)
        except Exception:
            self.logger.error(f"Unhandled exception ({exc_value}))")
            self.logger.debug(format_traceback())
            status, headers, body = self.response.text("Internal server error", 500)

        respond(status, headers)
        if inspect.isgeneratorfunction(body):
            yield from body
        else:
            yield body

    def handle(self, request:VRequest):
        return self.response.text("Vial.handle is not implemented", 501)

    def serve(self, host:str="", port:int=8080):
        """Start a development server"""
        self.logger.info(f"Starting HTTP server at {host}:{port}")
        server = wsgiref.simple_server.make_server(
                host,
                port,
                self,
                handler_class=VialRequestHandler
        )
        server.parent = self
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print()
            self.logger.info("Keyboard interrupt. Shutting down...")
            server.server_close()
