#!/usr/bin/env python3

import http.server
import socket
from typing import Annotated, Any

import typer

from promexp import Promexp
from promexp.logger import logger as logging


def str_to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return value
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    if value.lower() in ("false", "0", "no", "off"):
        return False
    return bool(value)


def parse_list_option(val) -> list:
    if not val:
        return []
    if isinstance(val, str):
        items = []
        parts = val.split(",") if "," in val else val.split()
        for p in parts:
            p_stripped = p.strip()
            if p_stripped:
                items.append(p_stripped)
        return items
    items = []
    for item in val:
        items.extend(parse_list_option(item))
    return items


def parse_tags_option(val):
    parsed = {}
    if not val:
        return parsed
    if isinstance(val, str):
        parts = val.split(",") if "," in val else val.split()
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k.strip()] = v.strip()
        return parsed
    for item in val:
        parsed.update(parse_tags_option(item))
    return parsed


def merge_settings(base, override):
    if not override:
        return
    for k, v in override.items():
        if k == "provider_settings" and isinstance(v, dict):
            if "provider_settings" not in base:
                base["provider_settings"] = {}
            for pk, pv in v.items():
                if pk not in base["provider_settings"]:
                    base["provider_settings"][pk] = {}
                if isinstance(pv, dict) and isinstance(
                    base["provider_settings"][pk], dict
                ):
                    base["provider_settings"][pk].update(pv)
                else:
                    base["provider_settings"][pk] = pv
        elif k == "tags" and isinstance(v, dict):
            if "tags" not in base:
                base["tags"] = {}
            base["tags"].update(v)
        else:
            base[k] = v


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    promexp: Promexp | None = None

    def log_message(self, format, *args):
        logging.debug(f"{self.address_string()} - - {format % args}")

    def do_GET(self):
        if self.path == "/metrics":
            try:
                if self.promexp is None:
                    raise RuntimeError("Promexp instance not set on MetricsHandler")
                content = self.promexp.render()
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
        self.logger.info(f"Starting HTTP server at {host or '*'}:{port}")
        server_address = (host, port)
        httpd = http.server.HTTPServer(server_address, MetricsHandler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt. Shutting down...")
            httpd.server_close()


app = typer.Typer(
    name="promexp",
    help="Prometheus exporter for Nebula",
)


@app.command()
def main(
    listen_address: Annotated[
        str,
        typer.Option(
            help="Listen address",
            envvar="PROMEXP_LISTEN_ADDRESS",
        ),
    ] = "",
    listen_port: Annotated[
        int,
        typer.Option(
            help="Listen port",
            envvar="PROMEXP_LISTEN_PORT",
        ),
    ] = 9731,
    prefix: Annotated[
        str,
        typer.Option(
            help="Metrics prefix",
            envvar="PROMEXP_PREFIX",
        ),
    ] = "nebula",
    hostname: Annotated[
        str | None,
        typer.Option(
            help="Include hostname tag (True/False or custom hostname string)",
            envvar="PROMEXP_HOSTNAME",
        ),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option(
            help="Extra tags in KEY=VALUE format",
        ),
    ] = None,
    caspar_host: Annotated[
        str | None,
        typer.Option(
            help="CasparCG server host",
            envvar="PROMEXP_CASPAR_HOST",
        ),
    ] = None,
    caspar_port: Annotated[
        int,
        typer.Option(
            help="CasparCG server port",
            envvar="PROMEXP_CASPAR_PORT",
        ),
    ] = 5250,
    caspar_osc_port: Annotated[
        int,
        typer.Option(
            help="CasparCG server OSC port",
            envvar="PROMEXP_CASPAR_OSC_PORT",
        ),
    ] = 6250,
    caspar_heartbeat_interval: Annotated[
        int,
        typer.Option(
            help="CasparCG heartbeat interval",
            envvar="PROMEXP_CASPAR_HEARTBEAT_INTERVAL",
        ),
    ] = 10,
    nvidia_smi_path: Annotated[
        str | None,
        typer.Option(
            help="Path to nvidia-smi binary",
            envvar="PROMEXP_NVIDIA_SMI_PATH",
        ),
    ] = None,
    storage: Annotated[
        list[str] | None,
        typer.Option(
            help="Storage mountpoint whitelist",
            envvar="PROMEXP_STORAGES",
        ),
    ] = None,
    network_interface: Annotated[
        list[str] | None,
        typer.Option(
            help="Network interfaces whitelist",
            envvar="PROMEXP_NETWORK_INTERFACES",
        ),
    ] = None,
    network_ignore_inactive: Annotated[
        bool,
        typer.Option(
            help="Ignore inactive network interfaces",
            envvar="PROMEXP_NETWORK_IGNORE_INACTIVE",
        ),
    ] = True,
):
    settings_dict = {
        "host": "",
        "port": 9731,
        "hostname": True,
        "tags": {},
        "prefix": "nebula",
        "provider_settings": {
            "casparcg": {
                "host": "127.0.0.1",
                "port": 5250,
                "osc_port": 6250,
                "heartbeat_interval": 10,
                "force": False,
            }
        },
    }

    override = {}
    if listen_address is not None:
        override["host"] = listen_address
    if listen_port is not None:
        override["port"] = listen_port
    if prefix is not None:
        override["prefix"] = prefix
    if hostname is not None:
        override["hostname"] = str_to_bool(hostname)

    parsed_tags = parse_tags_option(tag)
    if parsed_tags:
        override["tags"] = parsed_tags

    prov_settings = {}

    def get_prov(name):
        if name not in prov_settings:
            prov_settings[name] = {}
        return prov_settings[name]

    if caspar_host:
        caspar_settings = {}
        caspar_settings["host"] = caspar_host
        caspar_settings["port"] = caspar_port
        caspar_settings["osc_port"] = caspar_osc_port
        caspar_settings["heartbeat_interval"] = caspar_heartbeat_interval
        prov_settings["casparcg"] = caspar_settings

    # NVIDIA specific
    if prov_settings.get("nvidia") is not None:
        nvidia = get_prov("nvidia")
        if nvidia_smi_path is not None:
            nvidia["smi_path"] = nvidia_smi_path

    # Storage specific
    # if prov_settings.get("storage") is not None:
    # storage = get_prov("storage")
    # if storages
    #     storage["storages"] = parse_list_option(storages)

    # Network specific
    # if prov_settings.get("network") is not None:
    #     network = get_prov("network")
    #     if network_interfaces:
    #         network["interfaces"] = parse_list_option(network_interfaces)
    #     if network_ignore_inactive is not None:
    #         network["ignore_inactive"] = network_ignore_inactive

    if prov_settings:
        override["provider_settings"] = prov_settings

    tags = {}

    # Apply hostname configuration
    if hostname is None:
        tags["hostname"] = socket.gethostname()
    elif hostname:
        tags["hostname"] = str(hostname)


    # Initialize promexp
    promexp = Promexp(
        prefix=settings_dict["prefix"],
        tags=tags,
        provider_settings=prov_settings,
        logger=logging,
    )

    # Set promexp on MetricsHandler class
    MetricsHandler.promexp = promexp

    server = Server("promexp", logger=logging)
    server.serve(listen_address, listen_port)


if __name__ == "__main__":
    app()
