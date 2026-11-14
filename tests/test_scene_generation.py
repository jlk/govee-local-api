"""Tests for the scene registry generator in scripts/fetch_scene_library.py."""

import base64
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_scene_library as fsl  # noqa: E402

BLOB = bytes([0x0A, 0x01, 0x03, 0xAA, 0xBB, 0xCC])


def _scene(name, code, scene_type=0, param=b"", scene_id=None, variant=""):
    """A library entry as extract_scenes() returns it."""
    return {
        "name": f"{name} {variant}".strip(),
        "code": code,
        "type": scene_type,
        "effects": 2 if variant else 1,
        "param": bool(param),
        "param_data": base64.b64encode(param).decode() if param else "",
        "scene_id": scene_id if scene_id is not None else code,
        "scene": name,
        "variant": variant,
    }


LIBRARY = [
    _scene("Rainbow", 22),
    _scene("Aurora", 33742, scene_type=6, param=BLOB),
    _scene("Dusk", 33803, scene_type=6, param=BLOB, scene_id=1),
    _scene("Dusk", 33804, scene_type=6, param=BLOB, scene_id=2),
    # A type-2 blob scene: never kept, even for verified models.
    _scene("Forest", 1234, scene_type=2, param=b"\x02\x01"),
]


def test_verified_model_keeps_parameter_scenes_without_the_prefix():
    entries = dict(fsl.model_scene_entries("H3A53", LIBRARY))

    assert entries["Rainbow"] == 22
    expected = [33742, base64.b64encode(BLOB[1:]).decode()]
    assert entries["Aurora"] == expected
    assert "Forest" not in entries


def test_other_models_keep_only_firmware_scenes():
    assert fsl.model_scene_entries("H6008", LIBRARY) == [("Rainbow", 22)]


def test_distinct_scenes_with_the_same_name_are_numbered():
    names = [name for name, _ in fsl.model_scene_entries("H3A53", LIBRARY)]

    assert names == ["Rainbow", "Aurora", "Dusk", "Dusk 2"]


def test_parameter_blob_without_the_prefix_is_skipped():
    library = [_scene("Odd", 40000, scene_type=6, param=b"\x02\x01")]

    assert fsl.model_scene_entries("H3A53", library) == []


def test_firmware_code_above_one_byte_is_skipped():
    assert fsl.model_scene_entries("H6008", [_scene("Big", 300)]) == []


def test_build_model_scenes_keys_and_shares_sets():
    library = {"H3A53": LIBRARY, "H6008": LIBRARY, "H6006": LIBRARY}

    result = fsl.build_model_scenes(library)

    h3a53 = result["sets"][result["models"]["H3A53"]]
    assert set(h3a53) == {"rainbow", "aurora", "dusk", "dusk_2"}
    assert result["models"]["H6008"] == result["models"]["H6006"]
    assert result["sets"][result["models"]["H6008"]] == {"rainbow": 22}


def test_build_model_scenes_needs_param_data_for_verified_models():
    stale = [{k: v for k, v in _scene("Rainbow", 22).items() if k != "param_data"}]

    with pytest.raises(ValueError, match="param_data"):
        fsl.build_model_scenes({"H3A53": stale})


def test_ha_scene_names_include_parameter_scenes():
    names = fsl.build_ha_scene_names({"H3A53": LIBRARY})

    assert names == {
        "aurora": "Aurora",
        "dusk": "Dusk",
        "dusk_2": "Dusk 2",
        "rainbow": "Rainbow",
    }
