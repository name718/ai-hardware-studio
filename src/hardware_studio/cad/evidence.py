"""Traceable dimension inputs; provenance is recorded, never assumed verified."""

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

DimensionName = Literal[
    "base_length",
    "base_width",
    "base_thickness",
    "corner_radius",
    "hole_pitch_x",
    "hole_pitch_y",
    "standoff_height",
    "standoff_diameter",
    "hole_diameter",
    "minimum_wall",
]
DIMENSIONS = get_args(DimensionName)


class DimensionEvidence(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, allow_inf_nan=False, str_strip_whitespace=True
    )

    nominal_mm: float = Field(ge=0, le=300)
    uncertainty_mm: float = Field(
        ge=0, le=5, description="Worst-case ± input tolerance, not CAD precision"
    )
    source_kind: Literal["measurement", "manufacturer_document", "design_decision"]
    reference: str = Field(
        min_length=5, max_length=500, description="Document ID/URL or measurement record ID"
    )
    locator: str = Field(
        min_length=3, max_length=200, description="Drawing/page/feature or measurement method"
    )
    revision: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_uncertainty(self) -> "DimensionEvidence":
        if self.source_kind != "design_decision" and self.uncertainty_mm == 0:
            raise ValueError("Measurements and manufacturer dimensions need a nonzero uncertainty")
        return self


def assess_accuracy(parameters) -> dict:
    evidence = parameters.dimension_evidence
    nominal = {name: getattr(parameters, name) for name in DIMENSIONS}
    uncertainty = {
        name: evidence[name].uncertainty_mm if name in evidence else 0.0 for name in DIMENSIONS
    }
    lower = {name: nominal[name] - uncertainty[name] for name in DIMENSIONS}
    upper = {name: nominal[name] + uncertainty[name] for name in DIMENSIONS}
    margins = {
        "minimum_required_wall_mm": upper["minimum_wall"],
        "base_thickness_mm": lower["base_thickness"],
        "radial_wall_mm": (lower["standoff_diameter"] - upper["hole_diameter"]) / 2,
        "edge_x_mm": (lower["base_length"] - upper["hole_pitch_x"] - upper["standoff_diameter"]) / 2
        - upper["corner_radius"],
        "edge_y_mm": (lower["base_width"] - upper["hole_pitch_y"] - upper["standoff_diameter"]) / 2
        - upper["corner_radius"],
        "post_gap_x_mm": lower["hole_pitch_x"] - upper["standoff_diameter"],
        "post_gap_y_mm": lower["hole_pitch_y"] - upper["standoff_diameter"],
    }
    return {
        "input_status": "demonstration_only"
        if parameters.dimension_source == "fictional_demo"
        else "evidence_recorded",
        "source_independently_verified": False,
        "physical_fit_verified": False,
        "uncertainty_policy": "Independent worst-case intervals; no assumed error cancellation",
        "kernel_comparison_tolerance_mm": 1e-5,
        "input_uncertainty_mm": {
            name: uncertainty[name] if name in evidence else None for name in DIMENSIONS
        },
        "margin_basis": "recorded_input_intervals"
        if len(evidence) == len(DIMENSIONS)
        else "nominal_only_for_missing_evidence; not a verified worst-case bound",
        "worst_case_margins": margins,
        "missing_evidence": [name for name in DIMENSIONS if name not in evidence],
        "limitations": [
            "Recorded references do not prove that a measurement or document is authentic",
            "CAD numerical tolerance is not a manufacturing tolerance or physical accuracy claim",
            "PCB fit, fasteners, component clearances and shrinkage need separate validation",
        ],
    }
