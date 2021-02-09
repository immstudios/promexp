import time
import math
import threading
import fractions
import telnetlib

from nxtools.caspar import CasparCG as NXCaspar

from .osc_server import OSCServer
from ...provider import BaseProvider


class CasparCG(NXCaspar):
    """CasparCG which fails to connect silently"""

    def connect(self):
        """Create connection to CasparCG Server"""
        try:
            self.connection = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)
        except ConnectionRefusedError:
            return False
        except Exception:
            return False
        return True

    def disconnect(self):
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
        print("vol reset")
        v = self._volume
        self._volume = 0
        return v


class CasparOSCServer():
    def __init__(self, osc_port=6250):
        self.osc_port = osc_port
        self.channels = {}
        self.last_osc = time.time()
        self.osc_server = OSCServer("", self.osc_port, self.handle_osc)
        self.osc_thread = threading.Thread(target=self.osc_server.serve_forever, args=())
        self.osc_thread.name = 'OSC Server'
        self.osc_thread.start()

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

        self.last_osc = time.time()




class CasparCGHeartbeat(threading.Thread):
    def run(self):
        while 1:
            response = self.parent.query("VERSION")
            if not response:
                print("HB FAILED")
                self.parent.caspar.disconnect() 
            else:
                print("HB OK")
            time.sleep(10)


class CasparCGProvider(BaseProvider):
    name = "casparcg"

    def __init__(self, parent, settings):
        super(CasparCGProvider, self).__init__(parent, settings)
        self.host = settings.get("host", "192.168.5.23")
        self.port = settings.get("port", 5250)
        self.osc_port = settings.get("osc_port", 6250)

        self.caspar = CasparCG(self.host, self.port, timeout=.5)

        response = self.caspar.query("VERSION")

        if not response and settings.get("force", False):
            self.disable()
            return

        self.osc = CasparOSCServer(self.osc_port)

        self.heartbeat = CasparCGHeartbeat()
        self.heartbeat.parent = self
        self.heartbeat.start()
        

    def collect(self):
        tags = {}
        self.add("casparcg_connected", int(self.caspar.is_connected), **tags)

        for id_channel, channel in self.osc.channels.items():
            self.add("casparcg_peak_volume", channel.peak_volume)


