#!/usr/bin/env python3

import os
import json
import socket

from promexp import Promexp
from promexp.logger import logger as logging

settings = {
    "host" : "",
    "port" : 9731,
    "hostname" : True,
    "tags" : {},
    "prefix" : "nebula",
    "provider_settings" : {}
}

logging.show_time = True

settings_path = "settings.json"
if os.path.exists(settings_path):
    try:
        settings.update(json.load(open(settings_path)))
    except Exception:
        logging.error("Unable to parse {settings_path}. Using defaults.")

if settings["hostname"] is True:
    settings["tags"]["hostname"] = socket.gethostname()
elif type(settings["hostname"]) == str:
    settings["tags"]["hostname"] = settings["hostname"]

promexp = Promexp(
    prefix=settings["prefix"],
    tags=settings["tags"],
    provider_settings=settings["provider_settings"],
    logger=logging,
)

import http.server

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.debug(f"{self.address_string()} - - {format % args}")

    def do_GET(self):
        if self.path == "/metrics":
            try:
                content = promexp.render()
                encoded = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            except Exception:
                logging.error("Error rendering metrics")
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Internal Server Error")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Use /metrics GET request")


class Server:
    def __init__(self, app_name="promexp", logger=None):
        self.logger = logger or logging

    def serve(self, host: str, port: int):
        self.logger.info(f"Starting HTTP server at {host if host else '*'}:{port}")
        server_address = (host, port)
        httpd = http.server.HTTPServer(server_address, MetricsHandler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            self.logger.info("Keyboard interrupt. Shutting down...")
            httpd.server_close()


if __name__ == "__main__":
    server = Server("promexp", logger=logging)
    server.serve("", 9731)

