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

- [ ] Turn on **LAN Control** for the H3A53 in the Govee app; confirm it's on 192.168.1.x
- [ ] Capture its `scan` reply (IP, fingerprint, sku, firmware versions) and save it in the findings log
- [ ] Capture `devStatus` replies in several states: off, RGB, white temperature, a scene, and with segments set in the app. Look for extra fields beyond `onOff`/`brightness`/`color`/`colorTemInKelvin`
- [ ] Check the basic JSON commands with an unregistered sku (on/off only today), then with a provisional entry: `turn`, `brightness`, `colorwc` RGB, `colorwc` Kelvin at 1000 / 2000 / 9000 / 10000 (does the device accept below 2000 and above 9000?)
- [ ] Write a reusable R&D probe script (scan, status, send raw ptReal hex, log every datagram). Decide where it lives: `scripts/` if useful upstream, otherwise `specs/tools/`
- [ ] Optional: dump the OpenAPI capabilities (`GET /router/api/v1/user/devices` with your Govee API key) and save the H3A53 entry. Look for segment counts and any dual-layer capability
- [ ] Optional: capture what the app sends while changing upper/lower colours on one segment. Options: Android Bluetooth HCI snoop log (BLE frames match ptReal payloads), or check whether the app uses LAN at all (Wireshark on port 4003)

## Phase 2 — Baseline support (first upstreamable PR, closes #385)

- [ ] Add `"H3A53": create_with_capabilities(True, True, True, <segments>, temperature_range=(1000, 10000))` to `GOVEE_LIGHT_CAPABILITIES`. Decide on adding H3A51 (and H3A52?), which share the scene library, given we can't test them
- [ ] Run `uv run python scripts/generate_model_scenes.py` (expect the 4 firmware scenes) and let the pre-commit hook regenerate `SUPPORTED_DEVICES.md`
- [ ] Tests: registry entry (features, segment count, temperature range), `ColorMessage` clamping at 1000/10000 for this model, scenes loaded
- [ ] Check on the real device: power, brightness, RGB, Kelvin endpoints, each of the 4 scenes
- [ ] Commit the code (code-only commit); tick items here (specs-only commit)

## Phase 3 — Segment and dual-layer R&D

- [ ] Check the existing segment command (`33 05 15 01 RGB … <2-byte mask>`): send to mask bits 1–12 one at a time and record what lights up (a strand? the upper zone? both zones?)
- [ ] Try the mask bits above 12 (13–16), in case the second zone sits at bits 13–24 (needs a wider mask)
- [ ] Try candidate layer selectors: other `33 05 15` subcommands (`02`, `03`, …), a trailing layer byte, and 3-byte masks. Keep a table of frame → observed effect
- [ ] Try per-segment brightness (`33 05 15 02 <brightness> <mask>` on other models) and per-segment white/Kelvin
- [ ] Use the H6008 bulbs (192.168.1.139 / .232) as a known-good control for the probe tooling
- [ ] Find a status readback for segment state (the `status` command and its `pt` reply, which `StatusResponse` already parses)
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
