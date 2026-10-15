import copy

import pytest
from pydantic import ValidationError

from hardware_studio.cad.evidence import DIMENSIONS, assess_accuracy
from hardware_studio.cad.parameters import BracketParameters


@pytest.fixture
def sourced_parameters():
    # Synthetic test fixture only; never represents a real board or measurement.
    p = BracketParameters().model_dump()
    p["dimension_source"] = "user_measured"
    p["source_note"] = "Synthetic unit-test record; these are not real physical measurements."
    p["dimension_evidence"] = {
        name: {
            "nominal_mm": p[name],
            "uncertainty_mm": 0.05 if name in ("hole_pitch_x", "hole_pitch_y") else 0.0,
            "source_kind": "measurement"
            if name in ("hole_pitch_x", "hole_pitch_y")
            else "design_decision",
            "reference": "synthetic-fixture-001",
            "locator": f"test feature {name}",
            "revision": "test-only-1",
        }
        for name in DIMENSIONS
    }
    return p


def test_evidence_records_never_claim_physical_truth(sourced_parameters):
    p = BracketParameters.model_validate(sourced_parameters)
    assessment = assess_accuracy(p)
    assert assessment["input_status"] == "evidence_recorded"
    assert not assessment["source_independently_verified"]
    assert not assessment["physical_fit_verified"]
    assert not assessment["missing_evidence"]
    assert assessment["input_uncertainty_mm"]["hole_pitch_x"] == 0.05


@pytest.mark.parametrize("missing", list(DIMENSIONS))
def test_no_silent_defaults_for_real_inputs(sourced_parameters, missing):
    del sourced_parameters[missing]
    with pytest.raises(ValidationError, match="must be explicit"):
        BracketParameters.model_validate(sourced_parameters)


def test_real_inputs_without_evidence_are_rejected():
    with pytest.raises(ValidationError):
        BracketParameters(dimension_source="user_measured", source_note="Manually entered data")


def test_disagreement_with_source_is_rejected(sourced_parameters):
    sourced_parameters["hole_pitch_x"] += 0.2
    with pytest.raises(ValidationError, match="differs from"):
        BracketParameters.model_validate(sourced_parameters)


def test_unrecorded_dimension_is_rejected(sourced_parameters):
    del sourced_parameters["dimension_evidence"]["base_thickness"]
    with pytest.raises(ValidationError, match="missing_evidence"):
        BracketParameters.model_validate(sourced_parameters)


@pytest.mark.parametrize("uncertainty", [0.0, -0.1, float("nan"), float("inf")])
def test_measurement_uncertainty_must_be_nonzero_and_finite(sourced_parameters, uncertainty):
    sourced_parameters["dimension_evidence"]["hole_pitch_x"]["uncertainty_mm"] = uncertainty
    with pytest.raises(ValidationError):
        BracketParameters.model_validate(sourced_parameters)


def test_acceptable_nominal_wall_can_fail_under_uncertainty(sourced_parameters):
    p = copy.deepcopy(sourced_parameters)
    p["dimension_evidence"]["standoff_diameter"]["uncertainty_mm"] = 1.5
    with pytest.raises(ValidationError, match="Worst-case"):
        BracketParameters.model_validate(p)


def test_designed_hole_pitch_cannot_masquerade_as_measurement(sourced_parameters):
    sourced_parameters["dimension_evidence"]["hole_pitch_x"]["source_kind"] = "design_decision"
    with pytest.raises(ValidationError, match="requires measurement"):
        BracketParameters.model_validate(sourced_parameters)


def test_manufacturer_dimensions_require_their_own_records(sourced_parameters):
    sourced_parameters["dimension_source"] = "manufacturer_document"
    with pytest.raises(ValidationError, match="manufacturer_document evidence"):
        BracketParameters.model_validate(sourced_parameters)
    for name in ("hole_pitch_x", "hole_pitch_y"):
        sourced_parameters["dimension_evidence"][name]["source_kind"] = "manufacturer_document"
    assert (
        BracketParameters.model_validate(sourced_parameters).dimension_source
        == "manufacturer_document"
    )


@pytest.mark.integration
def test_metrology_detects_actual_wrong_hole_size():
    from hardware_studio.cad.metrology import measure_features
    from hardware_studio.cad.model import build_model

    p = BracketParameters()
    changed = p.model_dump()
    changed["hole_diameter"] = 3.4
    wrong = build_model(changed).val()
    measured = measure_features(wrong, p)
    assert not measured["checks"]["hole_axes_and_diameters_match"]
    assert all(h["diameter_mm"] == pytest.approx(3.4) for h in measured["holes"])


@pytest.mark.integration
def test_step_features_are_measured_not_copied_from_inputs(built_bundle):
    _, data = built_bundle
    report = data["report"]
    assert report["schema_version"] == 2
    for label in ("measured_features", "step_measured_features"):
        features = report[label]
        assert all(features["checks"].values())
        assert [h["diameter_mm"] for h in features["holes"]] == pytest.approx([3.2] * 4)
        assert [h["height_mm"] for h in features["posts"]] == pytest.approx([8.0] * 4)
    assert report["dimension_accuracy"]["input_status"] == "demonstration_only"
