"""End-to-end check of the library against a real device, step by step.

Run from the repo root:
  uv run python specs/tools/verify_library.py IP STEP [STEP...]
STEP is scene:<name> | rgb:R,G,B | kelvin:K | bright:N | segment:N,R,G,B | wait:S
Each step is followed by a short pause; the device is found via the
controller's manual discovery queue.
"""

import asyncio
import sys

sys.path.insert(0, "src")
from govee_local_api import GoveeController  # noqa: E402


async def main(ip: str, steps: list[str]) -> None:
    controller = GoveeController(
        listening_addresses="0.0.0.0", discovery_enabled=False, update_enabled=False
    )
    await controller.start()
    controller.add_device_to_discovery_queue(ip)
    for _ in range(50):
        device = controller.get_device_by_ip(ip)
        if device:
            break
        await asyncio.sleep(0.2)
    else:
        raise SystemExit(f"{ip} did not answer discovery")
    print(f"found {device.sku}: {len(device.capabilities.available_scenes)} scenes")
    for step in steps:
        kind, _, arg = step.partition(":")
        print("step", step, flush=True)
        if kind == "scene":
            await device.set_scene(arg)
        elif kind == "rgb":
            await device.set_rgb_color(*map(int, arg.split(",")))
        elif kind == "kelvin":
            await device.set_temperature(int(arg))
        elif kind == "bright":
            await device.set_brightness(int(arg))
        elif kind == "segment":
            n, r, g, b = map(int, arg.split(","))
            await device.set_segment_rgb_color(n, r, g, b)
        elif kind == "wait":
            await asyncio.sleep(float(arg))
            continue
        await asyncio.sleep(1.0)
    controller.cleanup()


asyncio.run(main(sys.argv[1], sys.argv[2:]))
