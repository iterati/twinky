import os

from xled.discover import xdiscover
from xled.control import ControlInterface

import layout

class Interface(ControlInterface):
    def __init__(self, device):
        super(Interface, self).__init__(device.ip_address)
        self.device = device
        self.layout = self.get_led_layout()['coordinates']

    def set_rt_frame_socket(self, frame, version, leds_number=None):
        # every interface sends through the first one's UDP client, aimed at its own host
        self.udpclient.destination_host = self.host
        super(Interface, self).set_rt_frame_socket(frame, version, leds_number)

class Lights:
    def __init__(self, count: int=2):
        dgen = xdiscover()
        self.interfaces = [Interface(next(dgen)) for _ in range(count)]
        for interface in self.interfaces[1:]:
            interface._udpclient = self.interfaces[0].udpclient

if __name__ == "__main__":
    # saves the tree's real layout, so the simulator can play it offline
    lights = Lights()
    layout.save(os.path.join(layout.LAYOUTS, "tree.json"), [i.layout for i in lights.interfaces])
    print("Saved", sum(len(i.layout) for i in lights.interfaces), "lights to layouts/tree.json")
