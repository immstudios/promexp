__all__ = ["NetworkProvider"]

import psutil

from ..provider import BaseProvider

class NetworkProvider(BaseProvider):
    name = "network"

    def __init__(self, parent, settings):
        super(NetworkProvider, self).__init__(parent, settings)

        self.interface_blacklist = ["lo"]
        self.interface_whitelist = []

        wl = self.get("interfaces", [])

        for interface in psutil.net_if_stats().keys():
            istat = psutil.net_if_stats()[interface]
            if not istat.isup:
                continue
            if interface in self.interface_blacklist:
                continue
            if wl and (interface not in wl):
                continue
            self.interface_whitelist.append(interface)


    def collect(self):
        netstat = psutil.net_io_counters(pernic=True)
        for interface in netstat.keys():
            if interface in self.interface_blacklist:
                continue

            if interface not in self.interface_whitelist:
                continue

            istat = netstat[interface]
            if istat.bytes_sent or not self.get("ignore_inactive", True):
                self.add("network_sent_bytes_total", istat.bytes_sent, interface=interface)
            if istat.bytes_recv or not self.get("ignore_inactive", True):
                self.add("network_recv_bytes_total", istat.bytes_recv, interface=interface)

