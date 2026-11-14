"""Send one command to a Govee device, then print its devStatus reply.

Run from the repo root:
  uv run python specs/tools/send.py IP on|off
  uv run python specs/tools/send.py IP bright N
  uv run python specs/tools/send.py IP rgb R G B
  uv run python specs/tools/send.py IP kelvin K        (raw, not clamped)
  uv run python specs/tools/send.py IP hex HEX...      (frames sent verbatim, caller adds checksum)
  uv run python specs/tools/send.py IP ptreal HEX...   (each frame padded to 19 bytes + checksum)
"""

import socket
import sys
import time

sys.path.insert(0, "src")
from govee_local_api.message import (  # noqa: E402
    BrightnessMessage,
    DevStatusMessage,
    GoveeMessage,
    HexMessage,
    OnOffMessage,
    PtRealMessage,
)


class ColorWC(GoveeMessage):
    command = "colorwc"


ip, cmd, *args = sys.argv[1:]
if cmd in ("on", "off"):
    msg: GoveeMessage = OnOffMessage(cmd == "on")
elif cmd == "bright":
    msg = BrightnessMessage(int(args[0]))
elif cmd == "rgb":
    r, g, b = map(int, args)
    msg = ColorWC({"color": {"r": r, "g": g, "b": b}, "colorTemInKelvin": 0})
elif cmd == "kelvin":
    msg = ColorWC({"color": {"r": 0, "g": 0, "b": 0}, "colorTemInKelvin": int(args[0])})
elif cmd == "hex":
    msg = HexMessage(args)
elif cmd == "ptreal":
    msg = PtRealMessage([bytes.fromhex(a).ljust(19, b"\0") for a in args])
else:
    sys.exit(__doc__)

rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
rx.bind(("0.0.0.0", 4002))
rx.settimeout(0.5)
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("SEND", msg.as_json())
tx.sendto(bytes(msg), (ip, 4003))
time.sleep(1.0)
tx.sendto(bytes(DevStatusMessage()), (ip, 4003))
end = time.time() + 2
while time.time() < end:
    try:
        data, addr = rx.recvfrom(4096)
    except socket.timeout:
        continue
    if addr[0] == ip:
        print("RECV", data.decode(errors="replace"))
