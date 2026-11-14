"""Recolour individual records of an H3A53 sceneType 6 scene, one variant per step.

Per step: white flash (marker) -> whole run blue -> variant -> hold.
Run from the repo root:
  uv run python specs/tools/scene_layers.py IP SCENE_NAME VARIANT [VARIANT...] [--dry]
VARIANT is "stock" or comma-separated "<record>:<rrggbb>" edits, e.g. "0:ff0000,1:00ff00",
optionally prefixed "@<code>/" to send under another scene code (e.g. "@40001/0:ff0000").
"""

import base64
import json
import socket
import sys
import time

sys.path.insert(0, "src")
from govee_local_api.message import ColorMessage, SceneCodeMessage  # noqa: E402


def records(blob: bytes) -> list[tuple[int, int]]:
    """(start, length) of each record in a type-6 blob (with its leading 0x0a)."""
    out, i = [], 2
    for _ in range(blob[1]):
        out.append((i + 1, blob[i]))
        i += 1 + blob[i]
    return out


def recolour(blob: bytes, edits: dict[int, bytes]) -> bytes:
    b = bytearray(blob)
    for idx, (start, _length) in enumerate(records(blob)):
        if idx in edits:
            count = b[start + 15]
            for c in range(count):
                p = start + 16 + 3 * c
                b[p : p + 3] = edits[idx]
    return bytes(b)


ip, name, *rest = sys.argv[1:]
dry = "--dry" in rest
variants = [v for v in rest if v != "--dry"]
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
for idx, (start, length) in enumerate(records(blob)):
    r = blob[start : start + length]
    print(
        f"record {idx}: len={length} header={r[:15].hex()} colors={r[15]} tail={r[-12:].hex()}"
    )

tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(msg) -> None:
    if not dry:
        tx.sendto(bytes(msg), (ip, 4003))


for n, v in enumerate(variants, 1):
    code = eff["sceneCode"]
    if v.startswith("@"):
        code_str, v = v[1:].split("/", 1)
        code = int(code_str)
    edits = (
        {}
        if v == "stock"
        else {int(k): bytes.fromhex(c) for k, c in (e.split(":") for e in v.split(","))}
    )
    param = recolour(blob, edits)[1:]  # drop the leading 0x0a
    print(f"step {n}: code={code} {v}", flush=True)
    if dry:
        continue
    send(ColorMessage(rgb=None, temperature=6500))
    time.sleep(1.0)
    send(ColorMessage(rgb=(0, 0, 255), temperature=None))
    time.sleep(1.5)
    send(SceneCodeMessage(code, param))
    time.sleep(12.0)
send(ColorMessage(rgb=(0, 0, 255), temperature=None))
print("done (left blue)")
