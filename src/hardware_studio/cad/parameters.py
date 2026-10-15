from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hardware_studio.cad.evidence import (
    DIMENSIONS,
    DimensionEvidence,
    DimensionName,
    assess_accuracy,
)


class BracketParameters(BaseModel):
    """Millimetres; origin at base centre in XY, underside Z=0."""

    model_config = ConfigDict(
        extra="forbid", strict=True, allow_inf_nan=False, str_strip_whitespace=True
    )

    units: Literal["mm"] = "mm"
    dimension_source: Literal["fictional_demo", "user_measured", "manufacturer_document"] = (
        "fictional_demo"
    )
    source_note: str = Field(
        default="Fictional demonstration values; not matched to any real PCB.",
        min_length=10,
        max_length=500,
    )
    base_length: float = Field(default=74.0, ge=10, le=300)
    base_width: float = Field(default=54.0, ge=10, le=300)
    base_thickness: float = Field(default=3.0, ge=1, le=20)
    corner_radius: float = Field(default=2.0, ge=0, le=10)
    hole_pitch_x: float = Field(default=50.0, ge=5, le=280)
    hole_pitch_y: float = Field(default=30.0, ge=5, le=280)
    standoff_height: float = Field(default=8.0, ge=1, le=60)
    standoff_diameter: float = Field(default=7.0, ge=3, le=30)
    hole_diameter: float = Field(default=3.2, ge=1, le=15)
    minimum_wall: float = Field(default=1.2, ge=0.8, le=5)
    dimension_evidence: dict[DimensionName, DimensionEvidence] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_geometry(self) -> "BracketParameters":
        if self.dimension_source != "fictional_demo":
            implicit = set(DIMENSIONS) - self.model_fields_set
            missing = set(DIMENSIONS) - self.dimension_evidence.keys()
            if implicit or missing:
                raise ValueError(
                    f"Non-demo dimensions must be explicit and traceable; "
                    f"implicit={sorted(implicit)}, missing_evidence={sorted(missing)}"
                )
            if self.source_note == type(self).model_fields["source_note"].default:
                raise ValueError("Non-demo inputs require a specific source_note")
            required_kind = (
                "measurement"
                if self.dimension_source == "user_measured"
                else "manufacturer_document"
            )
            for name in ("hole_pitch_x", "hole_pitch_y"):
                if self.dimension_evidence[name].source_kind != required_kind:
                    raise ValueError(f"{name} requires {required_kind} evidence")
        for name, evidence in self.dimension_evidence.items():
            if abs(evidence.nominal_mm - getattr(self, name)) > 1e-9:
                raise ValueError(f"{name} differs from its recorded source value")
            if name != "corner_radius" and evidence.nominal_mm - evidence.uncertainty_mm <= 0:
                raise ValueError(f"{name} uncertainty interval must remain positive")
            if evidence.nominal_mm < evidence.uncertainty_mm:
                raise ValueError(f"{name} uncertainty interval must remain nonnegative")
        if self.hole_diameter + 2 * self.minimum_wall > self.standoff_diameter:
            raise ValueError("standoff wall is thinner than minimum_wall")
        if min(self.hole_pitch_x, self.hole_pitch_y) <= self.standoff_diameter:
            raise ValueError("standoffs must not overlap or touch each other")
        if 2 * self.corner_radius >= min(self.base_length, self.base_width):
            raise ValueError("corner radius must be smaller than half the base size")
        # Conservative: entire post stays inside the base's unrounded rectangle.
        for pitch, size in (
            (self.hole_pitch_x, self.base_length),
            (self.hole_pitch_y, self.base_width),
        ):
            if pitch + self.standoff_diameter + 2 * (self.corner_radius + self.minimum_wall) > size:
                raise ValueError("standoffs need more clearance from the base edge")
        margins = assess_accuracy(self)["worst_case_margins"]
        if any(
            margins[name] < margins["minimum_required_wall_mm"] - 1e-9
            for name in ("base_thickness_mm", "radial_wall_mm", "edge_x_mm", "edge_y_mm")
        ):
            raise ValueError(
                "Worst-case dimension uncertainty violates minimum wall/edge clearance"
            )
        if min(margins["post_gap_x_mm"], margins["post_gap_y_mm"]) <= 0:
            raise ValueError("Worst-case dimension uncertainty allows standoff overlap")
        return self

    @property
    def centres(self) -> list[tuple[float, float]]:
        return [
            (sx * self.hole_pitch_x / 2, sy * self.hole_pitch_y / 2)
            for sx in (-1, 1)
            for sy in (-1, 1)
        ]
