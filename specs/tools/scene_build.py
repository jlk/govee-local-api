"""Build H3A53 sceneType 6 scenes from copies of one template record, varying zone fields.

Per step: white flash (marker) -> whole run blue -> scene -> hold.
Run from the repo root:
  uv run python specs/tools/scene_build.py IP CODE SPEC [CODE SPEC ...] [--dry]
SPEC is one or more records joined by "+", each "<byte3>:<tail-2>:<rrggbb>" in hex,
e.g. "00:00:ff0000+01:01:00ff00", optionally followed by ":<b1b2>" to set header
bytes 1-2 (e.g. "01:01:ff0000:0305") and then by "/<pos>=<hex>" byte overrides
(e.g. "01:01:ff0000/4=02"). The template is record 1 of Aurora, whose colours
showed up on the lower zone (2026-11-14).
"""

import base64
import json
import socket
import sys
import time

sys.path.insert(0, "src")
from govee_local_api.message import ColorMessage, SceneCodeMessage  # noqa: E402

lib = json.load(open("specs/research/scene_library_H3A53.json"))
lib = lib.get("data", lib)
aurora = base64.b64decode(
    next(
        e["scenceParam"]
        for c in lib["categories"]
        for s in c["scenes"]
        if s["sceneName"] == "Aurora"
        for e in s["lightEffects"]
        if e.get("scenceParam")
    )
)
i = 2 + 1 + aurora[2]  # skip 0a, count, record 0
TEMPLATE = aurora[i + 1 : i + 1 + aurora[i]]
assert TEMPLATE[15] == 2 and TEMPLATE[-1] == 0xFF, TEMPLATE.hex()


def record(byte3: int, tail: int, rgb: bytes, b12: bytes = b"") -> bytes:
    r = bytearray(TEMPLATE)
    if b12:
        r[1:3] = b12
    r[3] = byte3
    r[-2] = tail
    for c in range(r[15]):
        r[16 + 3 * c : 19 + 3 * c] = rgb
    return bytes(r)


def scene_param(spec: str) -> bytes:
    recs = []
    for part in spec.split("+"):
        part, *overrides = part.split("/")
        b3, tl, rgb, *b12 = part.split(":")
        recs.append(
            record(
                int(b3, 16),
                int(tl, 16),
                bytes.fromhex(rgb),
                bytes.fromhex(b12[0]) if b12 else b"",
            )
        )
        if overrides:
            r = bytearray(recs[-1])
            for o in overrides:
                pos, val = o.split("=")
                r[int(pos)] = int(val, 16)
            recs[-1] = bytes(r)
    # Leading 0x0a omitted: the device wants the blob without it.
    return bytes([len(recs)]) + b"".join(bytes([len(r)]) + r for r in recs)


args = [a for a in sys.argv[1:] if a != "--dry"]
dry = "--dry" in sys.argv
ip, pairs = args[0], args[1:]
steps = list(zip(pairs[0::2], pairs[1::2]))
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(msg) -> None:
    if not dry:
        tx.sendto(bytes(msg), (ip, 4003))


print("template:", TEMPLATE.hex())
for n, (code, spec) in enumerate(steps, 1):
    param = scene_param(spec)
    print(f"step {n}: code={code} {spec}  param={param.hex()}", flush=True)
    if dry:
        continue
    send(ColorMessage(rgb=None, temperature=6500))
    time.sleep(1.0)
    send(ColorMessage(rgb=(0, 0, 255), temperature=None))
    time.sleep(1.5)
    send(SceneCodeMessage(int(code), param))
    time.sleep(12.0)
send(ColorMessage(rgb=(0, 0, 255), temperature=None))
print("done (left blue)")
