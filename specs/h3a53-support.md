# H3A53 support plan

Working to-do list for adding the Govee **H3A53** (Permanent Outdoor Lights 2
Pro, 200 ft) to `govee-local-api`. Tick items (`- [x]`) as they land; record
findings in the [Findings log](#findings-log) as we go.

Branch: `feature/h3a53` · Upstream issue: [Galorhallen/govee-local-api#385](https://github.com/Galorhallen/govee-local-api/issues/385)

> Commit hygiene: this file and everything under `specs/` go in specs-only
> commits. Library, test and data changes go in their own commits so they can
> be cherry-picked to upstream cleanly.

## What we know (2026-11-14)

| Fact                    | Value                                                                                                                                          | Confidence                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Product                 | Permanent Outdoor Lights 2 Pro, 200 ft (H3A51 = 100 ft, H3A52 also exists)                                                                     | Confirmed (Govee product page)                                   |
| Lights                  | 84 heads on 12 strands                                                                                                                         | Govee spec; strand count from a review summary                   |
| "Two LEDs per node"     | Each head has an **upper and lower colour zone**, independently controlled, each RGB + warm/cool white ("RGBWWIC", "dual-layer colour effect") | Product page plus review summary (review page not read directly) |
| Kelvin range            | 1000–10000 K (library default is 2000–9000)                                                                                                    | Govee spec                                                       |
| Segments                | 12 (per issue #385)                                                                                                                            | Unverified: could be 12, 24 (12 × 2 zones) or 84                 |
| LAN API                 | Issue #385 says yes; the official list wasn't readable                                                                                         | Unverified: no scan reply on first probe                         |
| Firmware scenes         | 4 (`sceneType` 0, no blob): White Light 99, Illumination 98, Rainbow 22, Going Home 2                                                          | Confirmed (live library query)                                   |
| Library scenes          | 87 more, all `sceneType` 6 / `cmdVersion` 6 with a `scenceParam` blob: a format this library doesn't use yet                                   | Confirmed; H3A51's library is identical                          |
| Community protocol data | None: govee2mqtt, homebridge-govee, HA and the OpenAPI docs have nothing model-specific                                                        | Confirmed absence                                                |

Raw scene libraries: `specs/research/scene_library_H3A53.json` (and
`scene_library_H705D.json`, an older permanent-light model, for comparison).

## Phase 0 — Setup

- [x] Create branch (`feature/h3a53`) and point `origin` at the fork (`jlk/govee-local-api`), `upstream` at Galorhallen
- [x] Fix the test that failed on macOS (`test_reuseaddr_and_broadcast_are_set`)
- [x] Update CLAUDE.md (architecture, git workflow)
- [x] Desk research: product, OpenAPI, community projects, scene library

## Phase 1 — Device recon (get it talking on the LAN)

- [x] Turn on **LAN Control** for the H3A53 in the Govee app; confirm it's on 192.168.1.x
- [x] Capture its `scan` reply (IP, fingerprint, sku, firmware versions) and save it in the findings log
- [ ] Capture `devStatus` replies in several states: off, RGB, white temperature, a scene, and with segments set in the app. Look for extra fields beyond `onOff`/`brightness`/`color`/`colorTemInKelvin`
- [x] Check the basic JSON commands with an unregistered sku (on/off only today), then with a provisional entry: `turn`, `brightness`, `colorwc` RGB, `colorwc` Kelvin at 1000 / 2000 / 9000 / 10000 (does the device accept below 2000 and above 9000?)
- [ ] Write a reusable R&D probe script (scan, status, send raw ptReal hex, log every datagram). Decide where it lives: `scripts/` if useful upstream, otherwise `specs/tools/`
- [x] Optional: dump the OpenAPI capabilities (`GET /router/api/v1/user/devices` with your Govee API key) and save the H3A53 entry. Look for segment counts and any dual-layer capability
- [x] ~~Capture the app's BLE traffic~~: done 2026-11-14 with an iPhone and PacketLogger. **The H3A53's BLE link is encrypted**, so it can't be read (see findings)
- [x] Capture the iPhone's network traffic (`rvictl -s <UDID>`, then tshark on `rvi0`) while changing upper/lower colours with the phone's Wi-Fi **on**: does the app send LAN `ptReal` to 192.168.1.132:4003 (readable), or only cloud traffic (TLS)?

## Phase 2 — Baseline support (first upstreamable PR, closes #385)

- [ ] Add `"H3A53": create_with_capabilities(True, True, True, <segments>, temperature_range=(1000, 10000))` to `GOVEE_LIGHT_CAPABILITIES`. Decide on adding H3A51 (and H3A52?), which share the scene library, given we can't test them
- [ ] Run `uv run python scripts/generate_model_scenes.py` (expect the 4 firmware scenes) and let the pre-commit hook regenerate `SUPPORTED_DEVICES.md`
- [ ] Tests: registry entry (features, segment count, temperature range), `ColorMessage` clamping at 1000/10000 for this model, scenes loaded
- [ ] Check on the real device: power, brightness, RGB, Kelvin endpoints, each of the 4 scenes
- [ ] Commit the code (code-only commit); tick items here (specs-only commit)

## Phase 3 — Segment and dual-layer R&D

- [x] Check the existing segment command (`33 05 15 01 RGB … <2-byte mask>`): send to mask bits 1–12 one at a time and record what lights up (a strand? the upper zone? both zones?)
- [x] Try the mask bits above 12 (13–16), in case the second zone sits at bits 13–24 (needs a wider mask)
- [ ] Try candidate layer selectors: other `33 05 15` subcommands (`02`, `03`, …), a trailing layer byte, and 3-byte masks. Keep a table of frame → observed effect
- [ ] Try per-segment brightness (`33 05 15 02 <brightness> <mask>` on other models) and per-segment white/Kelvin
- [ ] Use the H6008 bulbs (192.168.1.139 / .232) as a known-good control for the probe tooling
- [x] Find a status readback for segment state (the `status` command and its `pt` reply, which `StatusResponse` already parses)
- [ ] Write up the confirmed command set in the findings log

## Phase 4 — Dual-layer API design and implementation

- [ ] Design how the capability model represents two zones per segment. Options: a `layers`/`zones` count on `GoveeLightCapabilities` plus a new feature flag, or doubling segments. Keep it backwards compatible for the HA integration
- [ ] New message class(es) for zone-addressed segment colour (and brightness/Kelvin if supported), with tests that pin the exact bytes
- [ ] `GoveeController` / `GoveeDevice` methods (e.g. `set_segment_rgb_color(segment, r, g, b, zone=…)`), with validation and tests
- [ ] Update the `example/main.py` REPL so it can drive both zones
- [ ] Check on the device; code-only commit

## Phase 5 — Type-6 library scenes (stretch)

- [ ] Decode the `sceneType` 6 / `cmdVersion` 6 `scenceParam` blob format: compare with the type-2 blobs in the H705D library and with what `SceneCodeMessage` sends
- [ ] Check whether `SceneCodeMessage` (the `a3` multi-frame stream plus `33 05 04` activation) plays a type-6 scene as-is; if not, find the needed changes
- [ ] If playable: extend `fetch_scene_library.py` / `generate_model_scenes.py` so they can emit blob scenes for models that need them, without changing existing models' output. Add tests

## Phase 6 — Wrap-up and upstream

- [ ] Full test suite plus `uvx pre-commit run --all-files` green
- [ ] Update README / CLAUDE.md for anything new (CLAUDE.md in a separate commit)
- [ ] Build a clean upstream branch from `upstream/develop`, cherry-picking only code/test/data commits; open the PR against Galorhallen with the findings summary
- [ ] Note what the HA `govee_light_local` integration needs to expose zones/scenes

## Findings log

<!-- Date each entry. Paste raw datagrams and hex frames verbatim. -->

- **2026-11-14:** First LAN scan from 192.168.1.193 (bind 0.0.0.0, multicast discovery): only the two H6008 bulbs replied (192.168.1.139, 192.168.1.232; firmware 1.01.26). No H3A53 reply.
- **2026-11-14:** With LAN Control on, the H3A53 answers multicast discovery and `devStatus`:

  ```text
  192.168.1.132 {"msg":{"cmd":"scan","data":{"ip":"192.168.1.132","device":"19:8B:C0:F8:C5:B5:1E:04","sku":"H3A53","bleVersionHard":"3.07.01","bleVersionSoft":"1.00.11","wifiVersionHard":"1.04.02","wifiVersionSoft":"1.06.18"}}}
  192.168.1.132 {"msg":{"cmd":"devStatus","data":{"onOff":0,"brightness":58,"color":{"r":0,"g":0,"b":0},"colorTemInKelvin":1000}}}
  ```

  - The `devStatus` reply has the standard four fields and nothing more: no per-zone or per-segment state.
  - `colorTemInKelvin: 1000` while off: the device reports 1000 K, below the library's 2000 K default minimum, which fits the 1000–10000 K spec. To check: is this the last white setting or a placeholder?
  - The library logs "Device H3A53 is not supported" and falls back to on/off only, as expected.

- **2026-11-14:** Basic JSON commands, sent raw to 192.168.1.132:4003 with no clamping, while watching the lights. Every command was echoed exactly by the following `devStatus`:

  | Command               | Observed                                                     |
  | --------------------- | ------------------------------------------------------------ |
  | `turn` 1              | On; both zones warm white (it was left at 1000 K)            |
  | `brightness` 100      | Brighter; status reports 100                                 |
  | `colorwc` rgb 255/0/0 | **Both** zones red                                           |
  | `colorwc` rgb 0/0/255 | **Both** zones blue                                          |
  | `colorwc` 1000 K      | Both zones, very orange                                      |
  | `colorwc` 2000 K      | Clearly less orange than 1000 K, so 1000 K is a real setting |
  | `colorwc` 9000 K      | Bluish white                                                 |
  | `colorwc` 10000 K     | Accepted; can't be told apart from 9000 K by eye             |

  - **Conclusion:** the standard JSON command set works and drives both zones together. Use `temperature_range=(1000, 10000)`; with the default range, `ColorMessage` would clamp away 1000–2000 K, which is clearly visible.
  - **Still open:** controlling each zone separately has to go through `ptReal` (Phase 3).

- **2026-11-14:** Segment command (`SegmentColorMessages`, `33 05 15 01 RGB 00×5 <mask> 00×5`), with everything first set blue via `colorwc`:

  | Frame (hex, with checksum)                 | Mask                   | Observed                                                                                                           |
  | ------------------------------------------ | ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
  | `33051501ff0000…0100…dc`                   | bit 1                  | No red seen from the user's position (1/12 of the run, about 17 ft, may have been out of view). Status stayed blue |
  | `33051501ff00000000000000ff0f00000000002d` | bits 1–12              | **Whole run red, both zones.** Status changed to 255/0/0                                                           |
  | `3305150100ff0000000000003f000000000000e2` | bits 1–6               | About half the run green, half red. Each head is the same colour in **both** zones. Status stayed red              |
  | `330515010000ff000000000000f000000000002d` | bits 13–16             | No visible change                                                                                                  |
  | `330515010000ff00000000000000ffffffffff22` | bits 17–56 (bytes 3–7) | No visible change                                                                                                  |

  - **Conclusions:** the standard 12-bit segment mask works, and each bit colours **both zones** of its heads. The bits beyond 12 that we tried don't reach a second zone. `devStatus` only reflects colour commands that cover the whole run.
  - **Mistakes during the session (for the record):** a mis-built `ptReal` sent five frames padded to 19 bytes, the first being `33 05 15 00 …`, with no visible effect reported. A frame with the mask shifted one byte, and possibly a frame with a bad checksum, were also sent. From then on every frame was built with the library classes.
  - **Type-6 scene blobs** (`specs/research/scene_library_H3A53.json`) are layered effect descriptions (colour lists, timing, layer counts, e.g. Forest `0a042b0002140c…`), not simple per-zone frames. Not decoded yet (Phase 5).

- **2026-11-14:** iPhone BLE capture (`govee 2026111401.pklg`, kept out of git via `.git/info/exclude`; iPhone18,2), Govee app with the phone's Wi-Fi off. GATT: writes to handle `0x001c` (write command), notifications on `0x0018`.
  - **Handshake:** phone → `e711 01` + 37 bytes; device → `e711 00` + 48 bytes. Looks like a session-key exchange.
  - **After that, every PDU is** a 4-byte big-endian counter (separate counters for each direction) + 36 bytes of ciphertext. That fits a 20-byte Govee frame plus a 16-byte AEAD tag (AES-GCM/CCM style). No plain `33`/`aa`/`a3` frames appear anywhere.
  - **Timing:** keepalive writes about every 3.00 s. Three longer, two-fragment writes (about 64 + 24 bytes) at roughly t=2370, 2379 and 2394 s, likely the user's colour actions.
  - **Conclusion:** getting the zone commands from BLE would mean reverse-engineering the app's key exchange. Parked. Try the LAN capture via `rvictl` next.
- **2026-11-14:** iPhone network capture (`rvictl` → `rvi0`, 240 s, phone Wi-Fi on) while the user set the whole run blue, then one segment's upper zone red and lower zone green in the app.
  - **The app controls the light through Govee's cloud only:** MQTT over TLS on port 8883 to AWS (`2600:1f18:…`, us-east-1), about 370-byte messages each way at t≈12, 25, 36, 43 and 54 s.
  - **No phone ↔ 192.168.1.132 traffic at all**, and nothing on UDP 4001–4003. The cloud channel is TLS with AWS IoT client certificates, so it can't be read either.
- **2026-11-14:** LAN readback attempts after the app had set per-zone colours: the `status` command and `ptReal` reads `aa01`, `aa0501`, `aaa501` all got **no reply**. `scan`/`devStatus` still answer by unicast (one multicast discovery pass missed the device, so multicast isn't fully reliable). `devStatus` still reported blue 0/0/255 (the last whole-run colour), with no zone information.
  - **Conclusion:** on this firmware the LAN `ptReal` channel is write-only, and the device doesn't report segment or zone state over the LAN.
- **2026-11-14:** Repeated the iPhone network capture with LAN Control confirmed **on**. The user noticed it had been off during the first capture; it seems to switch itself off. The phone was on home Wi-Fi (source `2601:600:…`, not cellular `2607:fb91:…`). Result: the same cloud MQTT/TLS exchanges to AWS (t≈11–56 s, burst at 132 s) and **zero** packets to 192.168.1.132 or UDP 4001–4003.
  - **Conclusion:** the Govee app never uses the LAN API for control, so sniffing can't reveal the zone command. Next routes: decompile the Android app, the OpenAPI capability dump, or batch trial-and-error on the LAN.
- **2026-11-14:** Trial batch "sub" (scratchpad `trial.py`; each step: white flash, then all blue, then candidate red on mask `ff0f`): `33 05 15 03`…`08` with the `01` layout. **No visible effect for any of them** (run twice, watched the second time).
- **2026-11-14:** OpenAPI capabilities (`GET /router/api/v1/user/devices`), saved to `specs/research/openapi_capabilities_H3A53.json`. The API key isn't stored anywhere.
  - `segmentedColorRgb` and `segmentedBrightness`: **12 segments** (indices 0–11). Brightness per segment is 0–100.
  - `colorTemperatureK` **1000–10000** (confirms the range), `colorRgb`, `brightness` 1–100, `powerSwitch`.
  - Also: `gradientToggle`, `dreamViewToggle`, `musicMode` (8 modes + sensitivity/autoColor/rgb), and `lightScene` / `diyScene` / `snapshot` (options empty in this listing; they come from the scenes endpoint).
  - **No dual-layer / upper-lower zone capability.** Govee's public API models the H3A53 as a plain 12-segment RGBIC light. Zone control only exists in the app.
