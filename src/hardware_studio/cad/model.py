"""Trusted CadQuery template, also copied verbatim into each delivery bundle.

Replay a saved bundle with `python model.py` from its directory. No caller-supplied
Python is executed by the MCP server. All dimensions are millimetres.
"""

import json
from pathlib import Path

import cadquery as cq

TEMPLATE_VERSION = "bracket-v1"


def build_model(p: dict) -> cq.Workplane:
    centres = [
        (sx * p["hole_pitch_x"] / 2, sy * p["hole_pitch_y"] / 2) for sx in (-1, 1) for sy in (-1, 1)
    ]
    base = cq.Workplane("XY").box(
        p["base_length"], p["base_width"], p["base_thickness"], centered=(True, True, False)
    )
    if p["corner_radius"] > 0:
        base = base.edges("|Z").fillet(p["corner_radius"])
    posts = (
        cq.Workplane("XY")
        .workplane(offset=p["base_thickness"])
        .pushPoints(centres)
        .circle(p["standoff_diameter"] / 2)
        .extrude(p["standoff_height"])
    )
    holes = (
        cq.Workplane("XY")
        .pushPoints(centres)
        .circle(p["hole_diameter"] / 2)
        .extrude(p["base_thickness"] + p["standoff_height"])
    )
    return base.union(posts).cut(holes).clean()


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    model = build_model(json.loads((root / "parameters.json").read_text()))
    cq.exporters.export(model, str(root / "replayed.step"))
    cq.exporters.export(model, str(root / "replayed.stl"), tolerance=0.05, angularTolerance=0.1)
