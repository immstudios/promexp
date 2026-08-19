__all__ = ["StorageProvider"]

import os
from typing import TYPE_CHECKING, Any, NamedTuple

import psutil

from promexp.logger import logger
from promexp.metrics import Metric
from promexp.provider import BaseProvider

if TYPE_CHECKING:
    from promexp.promexp import Promexp

# Pseudo filesystems which never hold user data. Only used for autodetection,
# explicitly configured mountpoints are always exported.

IGNORED_FSTYPES = frozenset(
    {
        "autofs",
        "binfmt_misc",
        "bpf",
        "cgroup",
        "cgroup2",
        "configfs",
        "debugfs",
        "devpts",
        "devtmpfs",
        "efivarfs",
        "fusectl",
        "hugetlbfs",
        "mqueue",
        "nsfs",
        "overlay",
        "proc",
        "procfs",
        "pstore",
        "ramfs",
        "rpc_pipefs",
        "securityfs",
        "selinuxfs",
        "squashfs",
        "sysfs",
        "tmpfs",
        "tracefs",
    }
)

IGNORED_MOUNTPOINTS = (
    "/boot",
    "/dev",
    "/proc",
    "/run",
    "/snap",
    "/sys",
    "/tmp",
    "/var/lib",
)


class Mount(NamedTuple):
    mountpoint: str  # path as seen by the host
    path: str  # path as seen by this process
    fstype: str


class StorageProvider(BaseProvider):
    name = "storage"

    exported_metrics = [
        Metric("storage_total_bytes", "gauge", "Size of the filesystem"),
        Metric(
            "storage_free_bytes",
            "gauge",
            "Space available to unprivileged users",
        ),
        Metric("storage_used_bytes", "gauge", "Used space"),
        Metric(
            "storage_usage_percent",
            "gauge",
            "Used space as a percentage of the space available to users",
        ),
    ]

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent, settings)

        self.whitelist = [m for m in self.get("storages", []) if m]
        self.disabled: set[str] = set()
        self.warned = False

    def local_path(self, mountpoint: str) -> str | None:
        """Translate a mountpoint of this process to a host mountpoint.

        Returns None for mountpoints outside of the host root.
        """
        if not self.host_root:
            return mountpoint
        if mountpoint == self.host_root:
            return "/"
        if mountpoint.startswith(self.host_root + "/"):
            return mountpoint[len(self.host_root) :]
        return None

    def is_whitelisted(self, mountpoint: str) -> bool:
        return any(
            mountpoint == m if m == "/" else mountpoint.lower().startswith(m.lower())
            for m in self.whitelist
        )

    def get_mounts(self) -> list[Mount]:
        """Return storages to be reported.

        The mount table is re-read on every collect, so storages mounted
        or unmounted while promexp is running are picked up.
        """
        mounts: list[Mount] = []
        for partition in psutil.disk_partitions(all=True):
            mountpoint = self.local_path(partition.mountpoint)
            if mountpoint is None:
                continue

            if self.whitelist:
                if not self.is_whitelisted(mountpoint):
                    continue
            elif partition.fstype in IGNORED_FSTYPES or mountpoint.startswith(
                IGNORED_MOUNTPOINTS
            ):
                continue

            # Single file bind mounts (/etc/hosts and friends injected by
            # docker) report the usage of their parent filesystem.
            if not os.path.isdir(partition.mountpoint):
                continue

            mounts.append(
                Mount(
                    mountpoint=mountpoint.replace("\\", "/"),
                    path=partition.mountpoint,
                    fstype=partition.fstype,
                )
            )

        if not mounts and not self.warned:
            logger.warning(
                f"No storage matching the configuration found"
                f"{f' in {self.host_root}' if self.host_root else ''}"
            )
        self.warned = not mounts

        return mounts

    def collect(self) -> None:
        for mount in self.get_mounts():
            if mount.mountpoint in self.disabled:
                continue
            try:
                usage = psutil.disk_usage(mount.path)
            except PermissionError:
                logger.warning(
                    f"Disabling {mount.mountpoint} check due to permission error"
                )
                self.disabled.add(mount.mountpoint)
                continue
            except Exception as e:
                logger.warning(f"Unable to check {mount.mountpoint}: {e}")
                continue

            if not usage.total:
                continue

            tags = {"mountpoint": mount.mountpoint, "fstype": mount.fstype}

            self.add("storage_total_bytes", usage.total, **tags)
            self.add("storage_free_bytes", usage.free, **tags)
            self.add("storage_used_bytes", usage.used, **tags)
            self.add("storage_usage_percent", usage.percent, **tags)
