__all__ = ["PSUtilProvider"]

import os
import time
from typing import TYPE_CHECKING, Any

import psutil

from promexp.metrics import Metric
from promexp.provider import BaseProvider

if TYPE_CHECKING:
    from promexp.promexp import Promexp

ARCSTATS_PATH = "/proc/spl/kstat/zfs/arcstats"


class PSUtilProvider(BaseProvider):
    name = "psutil"

    exported_metrics = [
        Metric("uptime_seconds", "gauge", "Time elapsed since the machine booted"),
        Metric("cpu_usage_percent", "gauge", "CPU utilization since the last scrape"),
        Metric("memory_total_bytes", "gauge", "Total physical memory"),
        Metric("memory_free_bytes", "gauge", "Physical memory which is not in use"),
        Metric(
            "memory_available_bytes",
            "gauge",
            "Memory available for new allocations without swapping",
        ),
        Metric(
            "memory_used_bytes",
            "gauge",
            "Memory which cannot be reclaimed on demand",
        ),
        Metric(
            "memory_cached_bytes",
            "gauge",
            "Reclaimable page cache, buffers and slab",
        ),
        Metric("memory_shared_bytes", "gauge", "tmpfs and shared memory"),
        Metric("memory_slab_bytes", "gauge", "Memory used by kernel data structures"),
        Metric(
            "memory_arc_bytes",
            "gauge",
            "Size of the ZFS adaptive replacement cache",
        ),
        Metric(
            "memory_usage_percent",
            "gauge",
            "Used memory as a percentage of the total memory",
        ),
        Metric("swap_total_bytes", "gauge", "Total swap space"),
        Metric("swap_free_bytes", "gauge", "Swap space which is not in use"),
        Metric(
            "swap_usage_percent",
            "gauge",
            "Used swap space as a percentage of the total swap space",
        ),
        Metric("disk_read_bytes_total", "counter", "Bytes read from all disks"),
        Metric("disk_write_bytes_total", "counter", "Bytes written to all disks"),
    ]

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent, settings)
        self.boot_time = psutil.boot_time()
        self.run_time = time.time()
        self.has_arcstats = os.path.exists(ARCSTATS_PATH)

    def collect(self) -> None:
        self.add("uptime_seconds", time.time() - self.boot_time)
        self.add("cpu_usage_percent", psutil.cpu_percent())
        self.collect_memory()
        self.collect_swap()
        self.collect_disk_io()

    def collect_memory(self) -> None:
        mem = psutil.virtual_memory()
        if not mem.total:
            return

        # Buffers and page cache are handed back to applications whenever they
        # are needed, so they must not be counted as used memory. tmpfs (shmem)
        # is a part of the page cache, but it cannot be reclaimed without swap,
        # so it is added back to the used memory.
        # Fields other than total/available/free are platform specific.

        cached = getattr(mem, "buffers", 0) + getattr(mem, "cached", 0)
        shared = getattr(mem, "shared", 0)
        cached = max(cached - shared, 0)
        used = max(mem.total - mem.free - cached, 0)

        self.add("memory_total_bytes", mem.total)
        self.add("memory_free_bytes", mem.free)
        self.add("memory_available_bytes", mem.available)
        self.add("memory_used_bytes", used)
        self.add("memory_cached_bytes", cached)
        self.add("memory_shared_bytes", shared)
        self.add("memory_usage_percent", 100 * (used / mem.total))

        if slab := getattr(mem, "slab", 0):
            self.add("memory_slab_bytes", slab)

        if self.has_arcstats:
            self.collect_zfs_arc()

    def collect_zfs_arc(self) -> None:
        # ZFS ARC is not a part of the page cache, so it is reported as used
        # memory even though most of it is evictable on demand.
        # The file starts with a spec and a header line, the rest is
        # "name type value" triplets.
        try:
            with open(ARCSTATS_PATH) as f:
                for line in f:
                    fields = line.split()
                    if len(fields) == 3 and fields[0] == "size":
                        self.add("memory_arc_bytes", int(fields[2]))
                        return
        except (OSError, ValueError):
            self.has_arcstats = False

    def collect_swap(self) -> None:
        try:
            swp = psutil.swap_memory()
        except Exception:
            return
        if not swp.total:
            return
        self.add("swap_total_bytes", swp.total)
        self.add("swap_free_bytes", swp.free)
        self.add("swap_usage_percent", 100 * ((swp.total - swp.free) / swp.total))

    def collect_disk_io(self) -> None:
        try:
            dsk = psutil.disk_io_counters()
        except Exception:
            return
        if not dsk:
            return
        self.add("disk_read_bytes_total", dsk.read_bytes)
        self.add("disk_write_bytes_total", dsk.write_bytes)
