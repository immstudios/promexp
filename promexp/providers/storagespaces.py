__all__ = ["StorageSpacesProvider"]

import os
import time
import subprocess
import threading

from ..provider import BaseProvider


def get_ss_status():
    c = subprocess.Popen([
        "powershell.exe", 
        "Get-VirtualDisk | Format-Table FriendlyName,ResiliencySettingName,OperationalStatus, HealthStatus"
        ], 
        stderr=subprocess.PIPE, 
        stdout=subprocess.PIPE
    )
    stdout, _ = c.communicate()

    bounds = False
    result = []
    for line in stdout.decode("utf-8").split("\n"):
        if line.startswith("---"):
            bounds = [0]
            while True:
                pos = line.find(" -", bounds[-1])
                if pos == -1:
                    break
                bounds.append(pos+1)
            continue

        if not bounds:
            continue

        line = line.strip()
        if not line:
            continue

        title = line[bounds[0]:bounds[1]].strip()
        mode = line[bounds[1]:bounds[2]].strip()
        status = line[bounds[2]:bounds[3]].strip()
        health = line[bounds[3]:].strip()

        result.append({
            "title" : title,
            "mode" : mode,
            "status" : status,
            "health" : health
        })
        return result



class SSWorker(threading.Thread):
    def run(self):
        while 1:
            try:
                self.result = get_ss_status()
            except Exception:
                self.logger.error("Unable to get storage spaces status")

            time.sleep(30)


class StorageSpacesProvider(BaseProvider):
    name = "storagespaces"

    def __init__(self, parent, settings):
        super(StorageSpacesProvider, self).__init__(parent, settings)

        if os.name != "nt":        
            self.disable()
            return

        try:
            status = get_ss_status()
        except Exception:
            status = []

        if not status:
            self.disable()

        self.worker = SSWorker()
        self.worker.logger = self.logger
        self.worker.start()

    def collect(self):
        try:
            status = self.worker.result
        except Exception:
            status = []

        for sspace in status:
            tags = {
                "name" : sspace["title"],
                "mode" : sspace["mode"]
            }
            self.add("storage_space_healthy", int(sspace["health"] == "Healthy"), **tags)