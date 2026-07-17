__all__ = ["PSUtilProvider"]

import time
from typing import TYPE_CHECKING, Any

import psutil

from promexp.provider import BaseProvider

if TYPE_CHECKING:
    from promexp.promexp import Promexp


class PSUtilProvider(BaseProvider):
    name = "psutil"

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent, settings)
        self.boot_time = psutil.boot_time()
        self.run_time = time.time()

    def collect(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        try:
            swp = psutil.swap_memory()
        except Exception:
            swp = None
        try:
            dsk = psutil.disk_io_counters()
        except Exception:
            dsk = None

        self.add("uptime_seconds", time.time() - self.boot_time)
        self.add("cpu_usage", cpu)
        self.add("memory_bytes_total", mem.total)
        self.add("memory_bytes_free", mem.available)
        self.add("memory_usage", 100 * ((mem.total - mem.available) / mem.total))

        if swp and swp.total:
            self.add("swap_bytes_total", swp.total)
            self.add("swap_bytes_free", swp.free)
            self.add("swap_usage", 100 * ((swp.total - swp.free) / swp.total))

        if dsk:
            self.add("disk_read_bytes", dsk.read_bytes)
            self.add("disk_write_bytes", dsk.write_bytes)
