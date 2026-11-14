"""Send read-only queries to a Govee device and dump every reply (pt decoded to hex).

usage: query.py IP status | IP pt HEX [HEX...]   (pt frames padded to 19 bytes + checksum)
"""

import base64
import json
import socket
import sys
import time

sys.path.insert(0, "src")
from govee_local_api.message import PtRealMessage, StatusMessage

ip, kind, *args = sys.argv[1:]
msg = (
    StatusMessage()
    if kind == "status"
    else PtRealMessage([bytes.fromhex(a).ljust(19, b"\0") for a in args])
)
rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
rx.bind(("0.0.0.0", 4002))
rx.settimeout(0.3)
print("SEND", msg.as_json())
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(bytes(msg), (ip, 4003))
end = time.time() + 2.5
while time.time() < end:
    try:
        data, addr = rx.recvfrom(8192)
    except socket.timeout:
        continue
    if addr[0] != ip:
        continue
    print("RECV", data.decode(errors="replace"))
    try:
        d = json.loads(data)["msg"]["data"]
        for k in ("pt", "op"):
            v = d.get(k)
            if isinstance(v, str):
                print("  pt:", base64.b64decode(v).hex())
            elif isinstance(v, dict):
                for f in v.get("command", []):
                    print("  op:", base64.b64decode(f).hex())
    except Exception as e:
        print("  (decode:", e, ")")
