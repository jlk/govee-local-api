"""Run a numbered batch of candidate ptReal frames against a Govee device.

Per step: white flash (marker) -> whole run blue -> candidate -> hold.
usage: trial.py IP BATCH [--dry]
"""

import socket
import sys
import time

sys.path.insert(0, "src")
from govee_local_api.message import ColorMessage, PtRealMessage

RED = bytes([255, 0, 0])
ALL12 = b"\xff\x0f"


def seg(sub=1, rgb=RED, mid=bytes(5), mask=ALL12, tail=bytes(5), op=0x15):
    return bytes([0x33, 0x05, op, sub]) + rgb + mid + mask + tail


def put(frame, pos, val):
    b = bytearray(frame)
    b[pos] = val
    return bytes(b)


BATCHES = {
    # sub-command sweep, same layout as the working 33 05 15 01
    "sub": [(f"33 05 15 {s:02x}", seg(sub=s)) for s in (3, 4, 5, 6, 7, 8)],
    # candidate layer/zone selector in the reserved bytes of the 01 frame
    "layer": [
        ("byte7=01", put(seg(), 7, 1)),
        ("byte7=02", put(seg(), 7, 2)),
        ("byte11=01", put(seg(), 11, 1)),
        ("byte11=02", put(seg(), 11, 2)),
        ("byte14=01", put(seg(), 14, 1)),
        ("byte14=02", put(seg(), 14, 2)),
    ],
    # other 33 05 xx opcodes with RGB + 12-bit mask straight after the opcode
    "opcode": [
        (f"33 05 {o:02x} RGB mask", bytes([0x33, 0x05, o]) + RED + ALL12)
        for o in (0x0B, 0x0C, 0x13, 0x16, 0x17, 0x1A)
    ],
}


def frame19(f):
    assert len(f) <= 19, f.hex()
    return f.ljust(19, b"\0")


ip, batch, *rest = sys.argv[1:]
dry = "--dry" in rest
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(msg):
    if not dry:
        tx.sendto(bytes(msg), (ip, 4003))


for n, (label, f) in enumerate(BATCHES[batch], 1):
    msg = PtRealMessage([frame19(f)])
    print(f"step {n}: {label:22s} {frame19(f).hex()}", flush=True)
    if dry:
        continue
    send(ColorMessage(rgb=None, temperature=6500))
    time.sleep(1.0)
    send(ColorMessage(rgb=(0, 0, 255), temperature=None))
    time.sleep(1.0)
    send(msg)
    time.sleep(5.0)
send(ColorMessage(rgb=(0, 0, 255), temperature=None))
print("done (left blue)")
