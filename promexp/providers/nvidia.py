__all__ = ["NVIDIAProvider"]

import os
import subprocess

from ..provider import BaseProvider

class NVIDIAProvider(BaseProvider):
    name = "nvidia"

    def __init__(self, parent, settings):
        super(NVIDIAProvider, self).__init__(parent, settings)

        smi_paths = [
                "c:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
                "/usr/bin/nvidia-smi",
                "/usr/local/bin/nvidia-smi"
            ]

        if self["smi_path"]:
            smi_paths.insert(0, self["smi_path"])

        for f in smi_paths:
            if os.path.exists(f):
                self.logger.info("nvidia-smi found. NVidia GPU metrics available.")
                self.smi_path = f
                break
        else:
            self.disable()


    def collect(self):
        #TODO: This method should be refactored

        request_modes = self.get("request_modes", ["utilization"])

        try:
            rawdata = subprocess.check_output([self.smi_path, "-q", "-d", "utilization"])
        except Exception:
            return

        rawdata = rawdata.decode("utf-8")
        modes = [
                ["Utilization",  "utilization"],
                ["GPU Utilization Samples", "gpu-samples"],
                ["Memory Utilization Samples", "mem-samples"],
                ["ENC Utilization Samples", "enc-samples"],
                ["DEC Utilization Samples", "dec-samples"],
            ]
        result = []
        gpu_id = -1
        current_mode = False
        gpu_stats = {}
        for line in rawdata.split("\n"):
            if line.startswith("GPU"):
                if gpu_id > -1:
                    result.append(gpu_stats)

                gpu_stats = {"id" : line.split(" ")[1].strip()}
                gpu_id += 1
            for m, mslug in modes:
                if line.startswith((" "*4) + m):
                    current_mode = mslug
                    break

            if current_mode in request_modes and line.startswith(" "*8):
                key, value = line.strip().split(":")
                key = key.strip()
                try:
                    value = float(value.strip().split(" ")[0])
                except:
                    value = 0
                if current_mode not in gpu_stats:
                    gpu_stats[current_mode] = {}
                gpu_stats[current_mode][key.lower()] =  value

        if gpu_id > -1:
            result.append(gpu_stats)

        for i, gpu in enumerate(result):
            metrics = gpu["utilization"]
            for key in metrics:
                value = metrics[key]
                if key == "gpu":
                    key = "usage"
                self.add(f"gpu_{key}", value, gpu_id=i)

