"""Try a3-stream framing variants for an H3A53 sceneType 6 library scene.

Per step: white flash (marker) -> whole run blue -> variant -> hold.
Run from the repo root:
  uv run python specs/tools/scene_framing.py IP SCENE_NAME [--dry]
"""

import base64
import json
import socket
import sys
import time

sys.path.insert(0, "src")
from govee_local_api.message import ColorMessage, PtRealMessage  # noqa: E402

PAYLOAD = 19  # frame bytes before the checksum


def a3_frames(marker: int, param: bytes) -> list[bytes]:
    """Same chunking as SceneCodeMessage._parameter_frames, with a chosen marker."""
    stream = bytearray([0xA3, 0x00, 0x01, 0x00, marker])
    count = 0
    last_index = 1
    for byte in param:
        if len(stream) % PAYLOAD == 0:
            count += 1
            stream.append(0xA3)
            last_index = len(stream)
            stream.append(count)
        stream.append(byte)
    stream[last_index] = 0xFF
    stream[3] = count + 1
    return [
        bytes(stream[o : o + PAYLOAD]).ljust(PAYLOAD, b"\0")
        for o in range(0, len(stream), PAYLOAD)
    ]


def activation(code: int) -> bytes:
    return (b"\x33\x05\x04" + code.to_bytes(2, "little")).ljust(PAYLOAD, b"\0")


ip, name, *rest = sys.argv[1:]
dry = "--dry" in rest
lib = json.load(open("specs/research/scene_library_H3A53.json"))
lib = lib.get("data", lib)
eff = next(
    e
    for c in lib["categories"]
    for s in c["scenes"]
    if s["sceneName"] == name
    for e in s["lightEffects"]
    if e.get("scenceParam")
)
blob = base64.b64decode(eff["scenceParam"])
assert blob[0] == 0x0A, blob[:2].hex()
code = eff["sceneCode"]
variants = [
    ("marker 06, full blob", 0x06, blob),
    ("marker 0a, blob minus 0a", 0x0A, blob[1:]),
    ("marker 02, blob minus 0a", 0x02, blob[1:]),
    ("marker 04, full blob", 0x04, blob),
]

tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(msg) -> None:
    if not dry:
        tx.sendto(bytes(msg), (ip, 4003))


for n, (label, marker, param) in enumerate(variants, 1):
    frames = a3_frames(marker, param) + [activation(code)]
    print(f"step {n}: {label}  ({len(frames)} frames)", flush=True)
    for f in frames:
        print("    ", f.hex())
    if dry:
        continue
    send(ColorMessage(rgb=None, temperature=6500))
    time.sleep(1.0)
    send(ColorMessage(rgb=(0, 0, 255), temperature=None))
    time.sleep(1.5)
    send(PtRealMessage(frames))
    time.sleep(12.0)
send(ColorMessage(rgb=(0, 0, 255), temperature=None))
print("done (left blue)")
