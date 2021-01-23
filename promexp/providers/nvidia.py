__all__ = ["NVIDIAProvider"]

import os
import subprocess

from xml.etree import ElementTree as ET


from ..provider import BaseProvider


def parse_percent(string):
    try:
        return float(string.split(" ")[0])
    except ValueError:
        return 0


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
        try:
            rawdata = subprocess.check_output([self.smi_path, "-q", "-x"])
        except Exception:
            self.logger.error("Unable to execute nvidia-smi")
            return
        rawdata = rawdata.decode("utf-8")

        try:
            xml = ET.XML(rawdata)
        except Exception:
            self.logger.error("Unable to parse nvidia-smi output")
            return

        for i, gpu in enumerate(xml.findall("gpu")):

            tags = {
                "id" : i,
                "model" : gpu.find("product_name").text
            }

            utilization = gpu.find("utilization")
            temperature = gpu.find("temperature")
            power = gpu.find("power_readings")

            self.add("gpu_usage", parse_percent(utilization.find("gpu_util").text), **tags)
            self.add("gpu_memory", parse_percent(utilization.find("memory_util").text), **tags)
            self.add("gpu_encoder", parse_percent(utilization.find("encoder_util").text), **tags)
            self.add("gpu_decoder", parse_percent(utilization.find("decoder_util").text), **tags)

            self.add("gpu_fan_speed", parse_percent(gpu.find("fan_speed").text), **tags)
            self.add("gpu_temperature", parse_percent(temperature.find("gpu_temp").text), **tags)
            self.add("gpu_power_draw", parse_percent(power.find("power_draw").text), **tags)




