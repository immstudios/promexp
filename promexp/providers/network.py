__all__ = ["NetworkProvider"]

import os
from typing import TYPE_CHECKING, Any

import psutil

from promexp.logger import logger
from promexp.metrics import Metric
from promexp.provider import BaseProvider

if TYPE_CHECKING:
    from promexp.promexp import Promexp

# Interfaces skipped unless an explicit whitelist is configured.
# Prefixes cover the virtual interfaces created by container and VM runtimes.

IGNORED_INTERFACES = ("lo",)
IGNORED_INTERFACE_PREFIXES = ("veth", "br-", "docker", "virbr", "vnet")


class NetworkProvider(BaseProvider):
    name = "network"

    exported_metrics = [
        Metric(
            "network_sent_bytes_total",
            "counter",
            "Bytes transmitted by the interface",
        ),
        Metric(
            "network_recv_bytes_total",
            "counter",
            "Bytes received by the interface",
        ),
    ]

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent, settings)

        self.whitelist = [i for i in self.get("interfaces", []) if i]
        self.ignore_inactive = self.get("ignore_inactive", True)

        # /proc/net is per network namespace, so a container attached to a
        # bridge network sees its own virtual interface only. Host counters
        # live in the network namespace of the host init process.

        self.net_dev_path: str | None = None
        if self.host_root:
            path = f"{self.host_root}/proc/1/net/dev"
            if os.access(path, os.R_OK):
                self.net_dev_path = path
            else:
                logger.warning(
                    f"Unable to read {path}. Network metrics are reported "
                    "for the container network namespace only."
                )

    def is_enabled(self, interface: str) -> bool:
        if self.whitelist:
            return interface in self.whitelist
        return interface not in IGNORED_INTERFACES and not interface.startswith(
            IGNORED_INTERFACE_PREFIXES
        )

    def get_counters(self) -> dict[str, tuple[int, int]]:
        """Return the {interface: (bytes_sent, bytes_recv)} mapping."""
        if self.net_dev_path is None:
            return {
                interface: (stat.bytes_sent, stat.bytes_recv)
                for interface, stat in psutil.net_io_counters(pernic=True).items()
            }

        # Receive columns come first (bytes packets errs drop fifo frame
        # compressed multicast), transmitted bytes are the 9th value.
        result: dict[str, tuple[int, int]] = {}
        try:
            with open(self.net_dev_path) as f:
                for line in f.readlines()[2:]:
                    interface, _, data = line.partition(":")
                    fields = data.split()
                    if len(fields) < 9:
                        continue
                    result[interface.strip()] = (int(fields[8]), int(fields[0]))
        except (OSError, ValueError) as e:
            logger.warning(f"Unable to read {self.net_dev_path}: {e}")
        return result

    def get_active(self, interfaces: list[str]) -> set[str]:
        """Return interfaces which are up.

        Interfaces which state cannot be determined are considered up.
        """
        if self.net_dev_path is None:
            stats = psutil.net_if_stats()
            return {i for i in interfaces if i not in stats or stats[i].isup}

        active = set()
        for interface in interfaces:
            try:
                with open(f"{self.host_root}/sys/class/net/{interface}/operstate") as f:
                    state = f.read().strip()
            except OSError:
                state = "unknown"
            if state != "down":
                active.add(interface)
        return active

    def collect(self) -> None:
        counters = self.get_counters()
        interfaces = [i for i in counters if self.is_enabled(i)]

        for interface in self.get_active(interfaces):
            sent, recv = counters[interface]
            if sent or not self.ignore_inactive:
                self.add("network_sent_bytes_total", sent, interface=interface)
            if recv or not self.ignore_inactive:
                self.add("network_recv_bytes_total", recv, interface=interface)
