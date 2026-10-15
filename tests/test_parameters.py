import pytest
from pydantic import ValidationError

from hardware_studio.cad.parameters import BracketParameters


def test_demo_is_explicitly_fictional():
    p = BracketParameters()
    assert p.dimension_source == "fictional_demo"
    assert len(set(p.centres)) == 4


@pytest.mark.parametrize(
    "patch",
    [
        {"base_length": -1.0},
        {"base_length": 301.0},
        {"base_length": float("nan")},
        {"base_length": float("inf")},
        {"base_length": "74"},
        {"base_length": True},
        {"base_thickness": 0.0},
        {"standoff_height": 1000.0},
        {"hole_diameter": 6.0},
        {"hole_pitch_x": 6.0},
        {"hole_pitch_y": 100.0},
        {"corner_radius": 10.0, "base_width": 20.0},
        {"units": "inch"},
        {"source_note": ""},
        {"dimension_source": "manufacturer_verified"},
        {"output_path": "/tmp/escape"},
        {"python_code": "print('arbitrary code')"},
    ],
)
def test_reject_invalid_geometry_and_unrecognised_fields(patch):
    with pytest.raises(ValidationError):
        BracketParameters.model_validate(patch)


def test_zero_radius_is_supported():
    assert BracketParameters(corner_radius=0.0).corner_radius == 0


def test_schema_is_closed_and_bounds_are_discoverable():
    schema = BracketParameters.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["base_length"]["maximum"] == 300
