__all__ = ["StorageProvider"]

import psutil

from ..provider import BaseProvider


class StorageProvider(BaseProvider):
    name = "storage"

    def __init__(self, parent, settings):
        super(StorageProvider, self).__init__(parent, settings)
        mountpoint_blacklist = ["/run", "/proc", "/sys", "/dev", "/snap", "/var/lib", "/tmp/snap", "/boot"]
        mountpoint_whitelist = self.get("storages", [])
        
        self.storages = []
        for storage in psutil.disk_partitions(all=True):
            if not all([not storage.mountpoint.startswith(b) for b in mountpoint_blacklist]):
                continue

            if mountpoint_whitelist:
                if not any([storage.mountpoint == b if b == "/" else storage.mountpoint.lower().startswith(b.lower()) for b in mountpoint_whitelist ]):
                    continue

            self.storages.append({
                    "device" : storage.device,
                    "mountpoint" : storage.mountpoint,
                    "fstype" : storage.fstype,
                })


    def collect(self):
        for storage in self.storages:
            if storage.get("disabled"):
                continue
            try:
                usage = psutil.disk_usage(storage["mountpoint"])
            except PermissionError:
                self.logger.warning(f"Disabling {storage['mountpoint']} check due to permission error")
                storage["disabled"] = True
                continue
            tags = {
                "mountpoint" : storage["mountpoint"].replace("\\", "/"),
                "fstype" : storage["fstype"],
            }
            self.add("storage_bytes_total", usage.total, **tags)
            self.add("storage_bytes_free", usage.free, **tags)
            self.add("storage_usage", usage.percent, **tags)