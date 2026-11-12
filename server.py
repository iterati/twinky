"""The simulator page's server, on one port: the built page (web/dist) over HTTP, and at /ws the
layout, then every frame's bytes as the tree is sent them, and from the page, its music messages."""
import asyncio
import email.utils
import json
import mimetypes
import os
import struct
import threading

from websockets.asyncio.server import ServerConnection, broadcast, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError
from websockets.http11 import Request, Response

PORT = 8016
DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist")

class Server:
    """Runs on its own event loop in its own thread. A page gets the layout as it connects, then one
    binary message a frame: the frame number (4 bytes, little-endian) and W, R, G, B a light. A page
    listening to music sends {"music": {...}} as text, the fields of music.Sound, for the beat clock."""
    def __init__(self, blender, port: int=PORT, dist: str=DIST):
        # every light where Pixel has it, after normalizing: x, y (its height, 0 to 1) and z, its
        # strand and index on the strand, and its angle round the trunk (0 to 1)
        places = [(strand, index)
                  for strand, interface in enumerate(blender.lights.interfaces)
                  for index in range(len(interface.layout))]
        self.layout = json.dumps({"layout": [
            {"x": pixel.x, "y": pixel.y, "z": pixel.z, "strand": strand, "index": index, "angle": pixel.t}
            for pixel, (strand, index) in zip(blender.pixels, places)
        ]})
        self.beat = blender.beat
        self.port = port
        self.dist = dist
        self.clients: set[ServerConnection] = set()
        self.number = 0
        self.loop = asyncio.new_event_loop()

    def start(self):
        # opened on the caller's thread, so a port in use stops twinky as it starts
        self.server = self.loop.run_until_complete(self._open())
        self.thread = threading.Thread(target=self.loop.run_forever, name="server")
        self.thread.start()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()

    def send(self, frame: bytes):
        """Takes a frame from the animation thread."""
        message = struct.pack("<I", self.number) + frame
        self.number += 1
        self.loop.call_soon_threadsafe(broadcast, self.clients, message)

    async def _open(self):
        # serve wants the loop running as it's made
        return await serve(self._connect, "localhost", self.port, process_request=self._page)

    async def _connect(self, connection: ServerConnection):
        await connection.send(self.layout)
        self.clients.add(connection)
        try:
            async for message in connection:
                self.beat.hear(json.loads(message)["music"])
        except ConnectionClosedError:
            pass  # a page gone without closing, as a tab closing can
        finally:
            self.clients.discard(connection)

    def _page(self, connection: ServerConnection, request: Request) -> Response | None:
        path = request.path.split("?")[0]
        if path == "/ws":
            return None
        file = os.path.normpath(os.path.join(self.dist, path.lstrip("/") or "index.html"))
        if not file.startswith(self.dist + os.sep) or not os.path.isfile(file):
            return connection.respond(404, "Not found (pnpm build makes the page)\n")
        with open(file, "rb") as f:
            body = f.read()
        headers = Headers([
            ("Date", email.utils.formatdate(usegmt=True)),
            ("Connection", "close"),
            ("Content-Length", str(len(body))),
            ("Content-Type", mimetypes.guess_type(file)[0]),
        ])
        return Response(200, "OK", headers, body)
