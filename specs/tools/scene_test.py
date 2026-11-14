"""Play an H3A53 library scene over LAN via SceneCodeMessage, optionally recoloured per layer.

usage: scene_test.py IP SCENE_NAME orig|edit [--dry]
  edit: every record whose layer byte (rec[-2]) is 0 -> all red, 1 -> all green
"""

import base64
import json
import socket
import sys

sys.path.insert(0, "src")
from govee_local_api.message import SceneCodeMessage

LAYER_RGB = {0: b"\xff\x00\x00", 1: b"\x00\xff\x00"}
ip, name, mode, *rest = sys.argv[1:]
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
blob = bytearray(base64.b64decode(eff["scenceParam"]))
if mode == "edit":
    i = 2
    for _ in range(blob[1]):
        L = blob[i]
        r = i + 1  # record spans blob[r : r+L]
        count = blob[r + 15]
        layer = blob[r + L - 2]
        for c in range(count):
            p = r + 16 + 3 * c
            blob[p : p + 3] = LAYER_RGB[layer]
        print(f"record layer={layer} colors={count} -> {LAYER_RGB[layer].hex()}")
        i = r + L
# sceneType 6 blobs start with a 0x0a byte that must not be sent (confirmed
# 2026-11-14: with it the device plays a fallback animation, without it the real scene).
param = bytes(blob[1:]) if blob[0] == 0x0A else bytes(blob)
msg = SceneCodeMessage(eff["sceneCode"], param)
frames = [base64.b64decode(f).hex() for f in msg.data["command"]]
print(f"{name} code={eff['sceneCode']} blob={len(blob)}B frames={len(frames)}")
for f in frames:
    print("  ", f)
if "--dry" not in rest:
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(bytes(msg), (ip, 4003))
    print("sent")
