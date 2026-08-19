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


def parse_number(string: str | None) -> float | None:
    """Parse a value such as "50.00 W" to a float.

    Returns None for values nvidia-smi reports as unavailable
    ("N/A", "Requested functionality has been deprecated"...)
    """
    if not string:
        return None
    try:
        return float(string.split(" ")[0])
    except ValueError:
        return None


def find_number(element: ET.Element | None, *names: str) -> float | None:
    """Return the value of the first child element which has a parseable one.

    Element names may be given in multiple variants, since nvidia-smi
    renames them from time to time.
    """
    if element is None:
        return None
    for name in names:
        child = element.find(name)
        if child is None:
            continue
        value = parse_number(child.text)
        if value is not None:
            return value
    return None


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

    def collect(self) -> None:
        try:
            raw = subprocess.check_output([self.smi_path, "-q", "-x"])  # noqa: S603
        except Exception:
            logger.exception("Unable to execute nvidia-smi")
            return
        rawdata = raw.decode("utf-8")

        try:
            xml = ET.XML(rawdata)
        except Exception:
            logger.exception("Unable to parse nvidia-smi output")
            return

        for i, gpu in enumerate(xml.findall("gpu")):
            product_name = gpu.find("product_name")
            model = product_name.text if product_name is not None else None
            tags: dict[str, Any] = {"id": i, "model": model or "unknown"}

            utilization = gpu.find("utilization")
            temperature = gpu.find("temperature")

            # Drivers 5xx and newer renamed power_readings to gpu_power_readings
            # and power_draw to average_power_draw / instant_power_draw
            power = gpu.find("gpu_power_readings")
            if power is None:
                power = gpu.find("power_readings")

            values = {
                "gpu_usage_percent": find_number(utilization, "gpu_util"),
                "gpu_memory_usage_percent": find_number(utilization, "memory_util"),
                "gpu_encoder_usage_percent": find_number(utilization, "encoder_util"),
                "gpu_decoder_usage_percent": find_number(utilization, "decoder_util"),
                "gpu_fan_speed_percent": find_number(gpu, "fan_speed"),
                "gpu_temperature_celsius": find_number(temperature, "gpu_temp"),
                "gpu_power_watts": find_number(
                    power,
                    "power_draw",
                    "average_power_draw",
                    "instant_power_draw",
                ),
            }

            # Unsupported metrics are reported as N/A. Skip them entirely
            # instead of publishing a bogus zero.
            for metric_name, value in values.items():
                if value is None:
                    continue
                self.add(metric_name, value, **tags)
