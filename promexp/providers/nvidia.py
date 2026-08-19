__all__ = ["NVIDIAProvider"]

import os
import subprocess
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

from promexp.logger import logger
from promexp.metrics import Metric
from promexp.provider import BaseProvider

if TYPE_CHECKING:
    from promexp.promexp import Promexp


def parse_number(string):
    try:
        return float(string.split(" ")[0])
    except ValueError:
        return 0


class NVIDIAProvider(BaseProvider):
    name = "nvidia"

    exported_metrics = [
        Metric("gpu_usage_percent", "gauge", "Utilization of the GPU core"),
        Metric("gpu_memory_usage_percent", "gauge", "Utilization of the GPU memory"),
        Metric(
            "gpu_encoder_usage_percent",
            "gauge",
            "Utilization of the nvenc video encoder",
        ),
        Metric(
            "gpu_decoder_usage_percent",
            "gauge",
            "Utilization of the nvdec video decoder",
        ),
        Metric("gpu_fan_speed_percent", "gauge", "Fan speed"),
        Metric("gpu_temperature_celsius", "gauge", "Temperature of the GPU core"),
        Metric("gpu_power_watts", "gauge", "Current power consumption"),
    ]

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent, settings)

        smi_paths = [
            "c:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
            "c:\\Windows\\System32\\nvidia-smi.exe",
            "/usr/bin/nvidia-smi",
            "/usr/local/bin/nvidia-smi",
        ]

        if self["smi_path"]:
            smi_paths.insert(0, self["smi_path"])

        for f in smi_paths:
            if os.path.exists(f):
                self.smi_path = f
                break
        else:
            self.disable()

    def collect(self):
        try:
            rawdata = subprocess.check_output([self.smi_path, "-q", "-x"])  # noqa: S603
        except Exception:
            logger.exception("Unable to execute nvidia-smi")
            return
        rawdata = rawdata.decode("utf-8")

        try:
            xml = ET.XML(rawdata)
        except Exception:
            logger.exception("Unable to parse nvidia-smi output")
            return

        for i, gpu in enumerate(xml.findall("gpu")):
            tags = {"id": i, "model": gpu.find("product_name").text}

            utilization = gpu.find("utilization")
            temperature = gpu.find("temperature")
            power = gpu.find("power_readings")

            self.add(
                "gpu_usage_percent",
                parse_number(utilization.find("gpu_util").text),
                **tags,
            )
            self.add(
                "gpu_memory_usage_percent",
                parse_number(utilization.find("memory_util").text),
                **tags,
            )
            self.add(
                "gpu_encoder_usage_percent",
                parse_number(utilization.find("encoder_util").text),
                **tags,
            )
            self.add(
                "gpu_decoder_usage_percent",
                parse_number(utilization.find("decoder_util").text),
                **tags,
            )
            self.add(
                "gpu_fan_speed_percent",
                parse_number(gpu.find("fan_speed").text),
                **tags,
            )
            self.add(
                "gpu_temperature_celsius",
                parse_number(temperature.find("gpu_temp").text),
                **tags,
            )
            self.add(
                "gpu_power_watts", parse_number(power.find("power_draw").text), **tags
            )
