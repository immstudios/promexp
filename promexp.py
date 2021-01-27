#!/usr/bin/env python3

import os
import json
import socket

from promexp import Promexp
from vial import Vial

from nxtools import logging

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

class Server(Vial):
    def handle(self, request):
        if request.method == "GET" and request.path == "/metrics":
            return self.response.text(promexp.render())
        return self.response.text(f"Use /metrics GET request", status=400)

if __name__ == "__main__":
    server = Server("promexp", logger=logging)
    server.serve("", 9731)
