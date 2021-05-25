import time
import math
import threading
import fractions
import telnetlib
import socket

from nxtools.caspar import CasparCG as NXCaspar
from nxtools import log_traceback, logging

from .osc_server import OSCServer
from ...provider import BaseProvider


class CasparCG(NXCaspar):
    """CasparCG which fails to connect silently"""
    verbose = False

    def connect(self, **kwargs):
        """Create connection to CasparCG Server"""
        try:
            self.connection = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)
        except ConnectionRefusedError:
            if self.verbose:
                logging.error("CasparCG: Connection refused")
            return False
        except socket.timeout:
            if self.verbose:
                logging.error("CasparCG: Connection timeout")
            return False
        except Exception:
            if self.verbose:
                log_traceback("CasparCG: Unable to connect")
            return False
        if self.verbose:
            logging.goodnews("CasparCG: Connected")
        return True

    def disconnect(self):
        if self.connection:
            logging.warning("CasparCG: Disconnected")
        self.connection = False

    @property
    def is_connected(self):
        return self.connection != False



class CasparChannel():
    def __init__(self):
        self.fps = fractions.Fraction(25, 1)
        self._volume = 0
        self.layers = {}

    def __getitem__(self, key):
        return self.layers.get(key, None)

    def handle_osc(self, address, *args):
        if address[0:2] ==  ["mixer", "audio"]:
            if address[2] == "volume":
                # Caspar 2.3
                v = (max(args) / 2147483647) * 100
                self._volume = max(self._volume, v)
                return
            elif len(address) == 4 and address[3] == "pFS":
                # Caspar 2.07
                self._volume = max(self._volume, args[0] * 100)
                return


    @property
    def peak_volume(self):
        v = self._volume
        self._volume = 0
        return v

    @property
    def dropped_frames(self):
        return 0


class CasparOSCServer():
    def __init__(self, osc_port=6250):
        self.osc_port = osc_port
        self.channels = {}
        self.last_message = time.time()
        self.osc_server = OSCServer("", self.osc_port, self.handle_osc)
        self.osc_thread = threading.Thread(target=self.serve, args=())
        self.osc_thread.name = 'OSC Server'
        self.osc_thread.start()

    def serve(self):
        while 1:
            try:
                self.osc_server.serve_forever()
            except Exception:
                log_traceback()
                time.sleep(1)

    def __getitem__(self, key):
        return self.channels.get(key, None)

    def handle_osc(self, address, *args):
        if type(address) == str:
            address = address.split("/")
        if len(address) < 2:
            return False
        if address[1] != "channel":
            return False
        try:
            channel = int(address[2])
        except (KeyError, ValueError):
            return False

        if not channel in self.channels:
            self.channels[channel] = CasparChannel()
        self.channels[channel].handle_osc(address[3:], *args)

        self.last_message = time.time()




class CasparCGHeartbeat(threading.Thread):
    def run(self):
        while 1:
            response = self.parent.query("VERSION")
            if not response:
                self.parent.caspar.disconnect()
            else:
                pass
            time.sleep(self.parent.heartbeat_interval)


class CasparCGProvider(BaseProvider):
    name = "casparcg"

    def __init__(self, parent, settings):
        super(CasparCGProvider, self).__init__(parent, settings)
        self.host = settings.get("host", "127.0.0.1")
        self.port = settings.get("port", 5250)
        self.osc_port = settings.get("osc_port", 6250)
        self.heartbeat_interval = settings.get("heartbeat_interval", 10)


        self.caspar = CasparCG(self.host, self.port, timeout=2)
        self.caspar.verbose = settings.get("force")

        response = self.query("VERSION")

        if (not response) and (not settings.get("force")):
            self.disable()
            return

        self.osc = CasparOSCServer(self.osc_port)

        self.heartbeat = CasparCGHeartbeat()
        self.heartbeat.parent = self
        self.heartbeat.start()

    def query(self, q):
        result = self.caspar.query(q, verbose=False)
        if result:
            self.enable()
        return result


    def collect(self):
        tags = {}
        self.add("casparcg_connected", int(self.caspar.is_connected), **tags)
        self.add("casparcg_idle_seconds", time.time() - self.osc.last_message, **tags)

        for id_channel, channel in self.osc.channels.items():
            tags = {"channel" : id_channel}
            self.add("casparcg_peak_volume", channel.peak_volume, **tags)
            self.add("casparcg_dropped_total", channel.dropped_frames, **tags)
