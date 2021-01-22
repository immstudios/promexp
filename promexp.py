#!/usr/bin/env python3

import os
import json
import socket


from promexp import Promexp
from vial import Vial


settings = {
    "host" : "",
    "port" : 9731,
    "tags" : {
        "hostname" : socket.gethostname()
    },
    "prefix" : "nebula",
    "providers" : {
    }
}

if os.path.exists("settings.json"):
    try:
        settings.update(json.load(open("settings.json")))
    except Exception:
        print("ERR")


promexp = Promexp(prefix=settings["prefix"], tags=settings["tags"])

class Server(Vial):
    def handle(self, request):
        if request.method == "GET" and request.path == "/metrics":
            return self.response.text(promexp.render())
        return self.response.text(f"Use /metrics GET request", status=400)


if __name__ == "__main__":
    server = Server("promexp")
    server.serve("", 9731)
