import socketserver
import time
from types import FunctionType

from .bundle import _BUNDLE_PREFIX
from .osc_types import OSCParseError
from .packet import OSCPacket


class OSCHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            packet = OSCPacket(self.request[0])
            for timed_msg in packet.messages:
                time.time()
                message = timed_msg.message
                self.server.handle(message.address, *message.params)
        except OSCParseError:
            pass


class OSCServer(socketserver.UDPServer):
    def __init__(self, host: str, port: int, handler: FunctionType) -> None:
        self.handle = handler
        super().__init__((host, port), OSCHandler)

    def verify_request(
        self, request: list[bytes], client_address: tuple[str, int]
    ) -> bool:
        data = request[0]
        return data.startswith((_BUNDLE_PREFIX, b"/"))
