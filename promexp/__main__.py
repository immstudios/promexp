#!/usr/bin/env python3

import http.server
import socket
import sys
from typing import Annotated, Any

import typer

from promexp.logger import log_traceback, logger
from promexp.promexp import Promexp
from promexp.version import __version__


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


def get_hostname(host_root: str | None) -> str:
    """Return the name of the machine promexp reports about.

    In a container, socket.gethostname() returns the container ID, which
    changes whenever the container is recreated, so the hostname of the
    monitored machine is read from the host root when available.
    """
    if host_root:
        try:
            with open(f"{host_root}/etc/hostname") as f:
                if name := f.read().strip().splitlines()[0]:
                    return name
        except (OSError, IndexError):
            logger.warning(f"Unable to read {host_root}/etc/hostname")
    return socket.gethostname()


def parse_list_option(val: str) -> list[str]:
    if not val:
        return []
    items = []
    parts = val.split(",") if "," in val else val.split()
    for p in parts:
        p_stripped = p.strip()
        if p_stripped:
            items.append(p_stripped)
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


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    promexp: Promexp | None = None

    def log_message(self, msg: str, *args) -> None:
        logger.debug(f"{msg % args} {self.client_address[0]}\n")

    def do_GET(self) -> None:
        if self.path == "/metrics":
            if self.promexp:
                try:
                    content = self.promexp.render()
                    encoded = content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except Exception:
                    log_traceback()
                else:
                    return
            else:
                logger.error("Promexp instance not initialized")

            logger.error("Error rendering metrics")
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
    def __init__(self) -> None:
        pass

    def serve(self, host: str, port: int) -> None:
        logger.info(f"Starting HTTP server at {host or '*'}:{port}")
        server_address = (host, port)
        httpd = http.server.HTTPServer(server_address, MetricsHandler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt. Shutting down...")
            httpd.server_close()


app = typer.Typer(
    name="promexp",
    help="Prometheus exporter for Nebula",
)


@app.command()
def main(  # noqa: C901, PLR0912, PLR0913
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit",
        ),
    ] = False,
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
    storages: Annotated[
        str | None,
        typer.Option(
            help="Comma separated storage mountpoint whitelist",
            envvar="PROMEXP_STORAGES",
        ),
    ] = None,
    host_root: Annotated[
        str | None,
        typer.Option(
            help="Directory the host root filesystem is mounted to "
            "(when running in a container)",
            envvar="PROMEXP_HOST_ROOT",
        ),
    ] = None,
    network_interfaces: Annotated[
        str | None,
        typer.Option(
            help="Comma separated network interfaces whitelist",
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
) -> None:

    if version:
        sys.stdout.write(__version__)
        sys.stdout.flush()
        sys.exit(0)

    override = {}
    if listen_address is not None:
        override["host"] = listen_address
    if listen_port is not None:
        override["port"] = listen_port
    if hostname is not None:
        override["hostname"] = str_to_bool(hostname)

    parsed_tags = parse_tags_option(tag)
    if parsed_tags:
        override["tags"] = parsed_tags

    #
    # Provider settings
    #

    prov_settings = {}

    # CasparCG specific

    caspar_settings = {}
    if caspar_host:
        caspar_settings["host"] = caspar_host
        caspar_settings["port"] = caspar_port
        caspar_settings["osc_port"] = caspar_osc_port
        caspar_settings["heartbeat_interval"] = caspar_heartbeat_interval
    prov_settings["casparcg"] = caspar_settings

    # NVIDIA specific

    nvidia_settings = {}
    if nvidia_smi_path:
        nvidia_settings["smi_path"] = nvidia_smi_path
    prov_settings["nvidia"] = nvidia_settings

    # Network specific

    network_settings = {}
    if network_interfaces:
        ifaces = parse_list_option(network_interfaces)
        network_settings["interfaces"] = ifaces

    if not network_ignore_inactive:
        network_settings["ignore_inactive"] = network_ignore_inactive
    else:
        network_settings["ignore_inactive"] = True

    prov_settings["network"] = network_settings

    # Storage specific

    storage_settings: dict[str, Any] = {}
    if storages:
        storage_settings["storages"] = parse_list_option(storages)
    prov_settings["storage"] = storage_settings

    #
    # Metric tags
    #

    tags = {}

    # Apply hostname to tags

    # --hostname may be a boolean (autodetect / do not tag at all)
    # or the name to be used instead of the autodetected one.

    if hostname is None or hostname.lower() in ("true", "1", "yes", "on"):
        tags["hostname"] = get_hostname(host_root)
    elif hostname.lower() not in ("false", "0", "no", "off"):
        tags["hostname"] = hostname

    #
    # Initialize promexp
    #

    promexp = Promexp(
        prefix=prefix,
        tags=tags,
        provider_settings=prov_settings,
        host_root=host_root or "",
    )

    # Set promexp on MetricsHandler class

    MetricsHandler.promexp = promexp

    server = Server()
    server.serve(listen_address, listen_port)


if __name__ == "__main__":
    app()
